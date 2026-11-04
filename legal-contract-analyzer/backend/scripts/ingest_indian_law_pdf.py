"""
Indian Law PDF Ingestion Engine
================================
Extracts, structures, and indexes official Indian Bare Acts and the Constitution of India from PDF documents.
Parses article/section numbers, titles, verbatim text, and page references, inserts them into PostgreSQL,
computes dense vector embeddings, and indexes them into Qdrant Cloud ('indian_legal_corpus').
"""

import os
import sys
import re
import uuid
import asyncio
import logging
from datetime import date
from typing import List, Dict, Any, Optional
import fitz  # PyMuPDF

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.db.session import AsyncSessionLocal, engine, Base
from app.db.models import LegalStatute, LegalSection
from app.services.embedding.embedder import embedding_service
from app.services.vector_store.qdrant_client import qdrant_service
from sqlalchemy import select

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("ingest_indian_law_pdf")

DEFAULT_CONSTITUTION_PDF = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../docs/95ef471035ee0b5e4e5b1cac3d3584c1.pdf")
)

def parse_constitution_pdf(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parses the official Constitution of India PDF into structured articles.
    Extracts article numbers, titles, verbatim content, and page numbers.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found at: {pdf_path}")

    logger.info(f"Opening Constitution PDF: {pdf_path}")
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    logger.info(f"Total pages: {total_pages}")

    # Regex matching Article definitions: e.g. '14. Equality before law.—' or '2[21A. Right to education.—'
    art_pattern = re.compile(
        r'(?:^|\n)\s*(?:\d+\[)?(\d+[A-Z]?)\.\s+([A-Z\[][^—\n]+(?:\n[^\n—]+)?)\s*—',
        re.MULTILINE
    )

    articles = []
    current_art = None

    # Articles begin around page 33 (Part I) and go up to page 283 (Article 395, Part XXII)
    # Page 284 onwards contains First Schedule to Twelfth Schedule and Appendices
    start_page = 32
    end_page = min(284, total_pages)
    logger.info(f"Extracting articles from page {start_page + 1} to {end_page}...")

    for page_idx in range(start_page, end_page):
        page_num = page_idx + 1
        page_text = doc[page_idx].get_text("text")

        # Filter out running headers and footnote definitions
        lines = page_text.split("\n")
        cleaned_lines = []
        for line in lines:
            l = line.strip()
            if not l:
                continue
            # Header lines like 'THE CONSTITUTION OF INDIA', '(Part III.—Fundamental Rights)', or page numbers
            if l.startswith("THE CONSTITUTION OF INDIA") or l.startswith("(Part ") or (l.isdigit() and len(l) <= 3):
                continue
            # Footnote markers at bottom: '1. Added by...', '1. Ins. by...', '1. Subs. by...'
            if re.match(r'^\d+\.\s+(?:Ins\.|Subs\.|Added\.|Certain|Omitted|See)\s+by', l):
                continue
            cleaned_lines.append(line)

        text = "\n".join(cleaned_lines)

        # Find all article starts on this page
        matches = list(art_pattern.finditer(text))

        if matches:
            for idx, m in enumerate(matches):
                num = m.group(1)
                raw_title = " ".join(m.group(2).split()).strip()

                # Filter out false positives
                if len(raw_title) > 200 or any(bad in raw_title.lower() for bad in ["ins. by", "subs. by", "added by", "w.e.f."]):
                    continue

                start_char = m.end()

                # If there was an article open, close its text
                if current_art:
                    preceding = text[:m.start()].strip()
                    if preceding:
                        current_art["content"] += "\n" + preceding
                    articles.append(current_art)

                # Current article content begins after '—'
                end_char = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
                art_content = text[start_char:end_char].strip()

                current_art = {
                    "section_number": f"Article {num}",
                    "num_raw": num,
                    "section_title": raw_title,
                    "content": art_content,
                    "page_number": page_num
                }
        else:
            # Continue text onto current open article
            if current_art:
                current_art["content"] += "\n" + text.strip()

    if current_art:
        articles.append(current_art)

    doc.close()

    # Deduplicate and clean up article contents
    unique_articles = []
    seen_articles = set()

    for a in articles:
        sec_num = a["section_number"]
        if sec_num in seen_articles:
            continue
        seen_articles.add(sec_num)

        # Clean content
        content = a["content"].strip()
        # Clean footnote brackets like 1[, 2[
        content = re.sub(r'\d+\[', '', content)
        content = re.sub(r'\]', '', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

        if len(content) < 15:
            content = f"Official constitutional provision of {sec_num} ({a['section_title']})."

        a["content"] = content
        unique_articles.append(a)

    logger.info(f"Extracted {len(unique_articles)} distinct Constitution Articles from PDF.")
    return unique_articles

async def ingest_constitution_pdf(pdf_path: Optional[str] = None, max_articles: Optional[int] = None):
    """
    Ingests the Constitution of India from PDF into Neon PostgreSQL and Qdrant Cloud.
    """
    path = pdf_path or DEFAULT_CONSTITUTION_PDF
    if not os.path.exists(path):
        raise FileNotFoundError(f"Constitution PDF not found at {path}")

    articles = parse_constitution_pdf(path)
    if max_articles:
        articles = articles[:max_articles]

    logger.info(f"Ingesting {len(articles)} Articles into database and vector store...")

    # 1. Initialize Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Upsert LegalStatute
    async with AsyncSessionLocal() as session:
        statute_res = await session.execute(
            select(LegalStatute).where(LegalStatute.act_name == "Constitution of India")
        )
        statute = statute_res.scalars().first()

        if not statute:
            statute = LegalStatute(
                id=str(uuid.uuid4()),
                act_name="Constitution of India",
                act_year=1950,
                act_number="Constituent Assembly of India",
                short_title="The Constitution of India",
                jurisdiction="Supreme Law of the Land",
                enactment_date=date(1949, 11, 26),
                commencement_date=date(1950, 1, 26),
                source_url="https://legislative.gov.in/constitution-of-india/",
                status="CURRENT"
            )
            session.add(statute)
            await session.commit()
            await session.refresh(statute)
            logger.info("Created LegalStatute: Constitution of India")
        else:
            logger.info(f"Found existing LegalStatute: {statute.act_name} (ID: {statute.id})")

        # 3. Upsert LegalSection records in PostgreSQL
        existing_sections_res = await session.execute(
            select(LegalSection.section_number).where(LegalSection.statute_id == statute.id)
        )
        existing_numbers = set(existing_sections_res.scalars().all())

        sections_to_add = []
        qdrant_points_to_embed = []

        for art in articles:
            sec_id = str(uuid.uuid4())
            sec_num = art["section_number"]
            title = art["section_title"]
            content = art["content"]
            page = art["page_number"]

            if sec_num not in existing_numbers:
                sec_obj = LegalSection(
                    id=sec_id,
                    statute_id=statute.id,
                    section_number=sec_num,
                    section_title=title,
                    content=content,
                    explanation_text=f"The Constitution of India, {sec_num}: {title}. Verbatim text from official Legislative Dept edition.",
                    status="CURRENT"
                )
                sections_to_add.append(sec_obj)

            # Prepare vector text
            embed_text = f"The Constitution of India {sec_num} ({title}): {content[:1000]}"
            qdrant_points_to_embed.append({
                "id": sec_id,
                "document_type": "STATUTE_SECTION",
                "act_name": "Constitution of India",
                "act_year": 1950,
                "section_number": sec_num,
                "title": f"{sec_num}: {title}",
                "content": content,
                "text_to_embed": embed_text,
                "source_url": f"https://legislative.gov.in/constitution-of-india/#page={page}",
                "status": "CURRENT"
            })

        if sections_to_add:
            session.add_all(sections_to_add)
            await session.commit()
            logger.info(f"Saved {len(sections_to_add)} new Constitution Sections to PostgreSQL.")
        else:
            logger.info("All sections already exist in PostgreSQL.")

    # 4. Generate Embeddings & Upsert to Qdrant Cloud
    logger.info(f"Generating embeddings for {len(qdrant_points_to_embed)} constitutional articles...")
    batch_size = 50
    all_points_ready = []

    for i in range(0, len(qdrant_points_to_embed), batch_size):
        batch = qdrant_points_to_embed[i:i + batch_size]
        texts = [b["text_to_embed"] for b in batch]
        embeddings = await embedding_service.get_batch_embeddings(texts)

        for item, emb in zip(batch, embeddings):
            item["vector"] = emb
            all_points_ready.append(item)

        logger.info(f"Embedded batch {i // batch_size + 1}/{(len(qdrant_points_to_embed) - 1) // batch_size + 1}")

    # Upsert to Qdrant collection
    qdrant_service.upsert_legal_points(all_points_ready)
    logger.info(f"Successfully upserted {len(all_points_ready)} articles into Qdrant '{settings.QDRANT_LEGAL_COLLECTION_NAME}'!")

    return {
        "status": "SUCCESS",
        "act_name": "Constitution of India",
        "total_articles_parsed": len(articles),
        "total_indexed": len(all_points_ready)
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest official Indian law PDF into PostgreSQL and Qdrant Cloud")
    parser.add_argument("--pdf", type=str, default=DEFAULT_CONSTITUTION_PDF, help="Path to PDF file")
    parser.add_argument("--max", type=int, default=None, help="Max articles to ingest (for testing)")
    args = parser.parse_args()

    asyncio.run(ingest_constitution_pdf(args.pdf, args.max))
