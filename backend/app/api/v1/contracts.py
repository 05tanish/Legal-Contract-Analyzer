from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import os
import aiofiles

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Contract, ContractChunk
from app.schemas.contract import ContractResponse, ContractDetailResponse
from app.services.ingestion.parser import DocumentParser
from app.services.ingestion.chunker import HierarchicalChunker
from app.services.embedding.embedder import embedding_service
from app.services.vector_store.qdrant_client import qdrant_service

router = APIRouter()

@router.post("/upload", response_model=ContractResponse)
async def upload_contract(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are currently supported.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(settings.UPLOAD_DIR, file.filename)

    # Save uploaded file asynchronously
    async with aiofiles.open(file_path, "wb") as buffer:
        content = await file.read()
        await buffer.write(content)

    # 1. Parse document structure using layout-aware parser
    try:
        parsed_doc = DocumentParser.parse_pdf(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse PDF document: {str(e)}")

    # Check for existing duplicate contract by file hash
    result = await db.execute(select(Contract).where(Contract.file_hash == parsed_doc["file_hash"]))
    existing_contract = result.scalars().first()
    if existing_contract:
        return existing_contract

    # Create Contract DB record
    contract = Contract(
        filename=file.filename,
        file_path=file_path,
        file_hash=parsed_doc["file_hash"],
        file_size_bytes=parsed_doc["file_size_bytes"],
        total_pages=parsed_doc["total_pages"],
        status="PROCESSING"
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    # 2. Chunk document using Hierarchical Chunker
    chunker = HierarchicalChunker()
    chunks_data = chunker.chunk_document(contract_id=contract.id, pages=parsed_doc["pages"])

    # 3. Embed child chunks & upsert to Qdrant
    child_chunks = [c for c in chunks_data if not c.get("is_parent", False)]
    if child_chunks:
        search_texts = [c.get("search_content", c["content"]) for c in child_chunks]
        embeddings = await embedding_service.get_batch_embeddings(search_texts)
        
        qdrant_points = []
        for c, emb in zip(child_chunks, embeddings):
            c_copy = c.copy()
            c_copy["vector"] = emb
            qdrant_points.append(c_copy)
        
        qdrant_service.upsert_chunks(qdrant_points)

    # 4. Save chunk records to relational DB
    db_chunks = [
        ContractChunk(
            id=c["id"],
            contract_id=contract.id,
            chunk_index=c["chunk_index"],
            page_number=c["page_number"],
            section_title=c.get("section_title"),
            content=c["content"],
            parent_id=c.get("parent_id"),
            is_parent=c.get("is_parent", False),
            metadata_json=c.get("metadata", {})
        )
        for c in chunks_data
    ]
    db.add_all(db_chunks)

    contract.status = "READY"
    await db.commit()
    await db.refresh(contract)

    return contract

@router.get("", response_model=List[ContractResponse])
async def list_contracts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).order_by(Contract.created_at.desc()))
    return result.scalars().all()

@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(contract_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == contract_id))
    chunks_count = len(chunks_res.scalars().all())

    data = ContractDetailResponse.model_validate(contract)
    data.chunks_count = chunks_count
    return data

@router.get("/{contract_id}/pdf")
async def get_contract_pdf(contract_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract or not os.path.exists(contract.file_path):
        raise HTTPException(status_code=404, detail="Contract PDF file not found.")
    return FileResponse(contract.file_path, media_type="application/pdf", filename=contract.filename)

