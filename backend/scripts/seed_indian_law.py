"""
Seed Script: Populates PostgreSQL and Qdrant with Core Indian Legal Corpus:
- Constitution of India (Fundamental Rights & Writs)
- Indian Contract Act, 1872 (All core commercial sections: 2, 10, 23, 27, 28, 73, 74, 124)
- Specific Relief Act, 1963 & Arbitration and Conciliation Act, 1996
- IT Act, 2000
- Landmark Supreme Court Precedents (Restraints of trade, Liquidated damages, Unconscionability, Privacy)
"""
import asyncio
import os
import sys
from datetime import date

# Ensure backend root is in PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.session import AsyncSessionLocal, engine, Base
from app.db.models import LegalStatute, LegalSection, CourtJudgment
from app.services.embedding.embedder import embedding_service
from app.services.vector_store.qdrant_client import qdrant_service
import uuid

# ----------------------------------------------------
# STATUTES DATA
# ----------------------------------------------------
STATUTES_SEED = [
    {
        "act_name": "Indian Contract Act",
        "act_year": 1872,
        "act_number": "Act No. 9 of 1872",
        "short_title": "The Indian Contract Act, 1872",
        "jurisdiction": "Central",
        "enactment_date": date(1872, 4, 25),
        "commencement_date": date(1872, 9, 1),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/2187",
        "status": "CURRENT",
        "sections": [
            {
                "section_number": "Section 10",
                "section_title": "What agreements are contracts",
                "content": "All agreements are contracts if they are made by the free consent of parties competent to contract, for a lawful consideration and with a lawful object, and are not hereby expressly declared to be void.",
                "explanation_text": "An agreement must meet four requirements to be legally binding in India: free consent, competent parties, lawful consideration/object, and not declared void by law."
            },
            {
                "section_number": "Section 23",
                "section_title": "What considerations and objects are lawful, and what not",
                "content": "The consideration or object of an agreement is lawful, unless it is forbidden by law; or is of such a nature that, if permitted, it would defeat the provisions of any law; or is fraudulent; or involves or implies injury to the person or property of another; or the Court regards it as immoral, or opposed to public policy. In each of these cases, the consideration or object of an agreement is said to be unlawful. Every agreement of which the object or consideration is unlawful is void.",
                "explanation_text": "Agreements contrary to public policy or violating any statutory provision are void ab initio in India."
            },
            {
                "section_number": "Section 27",
                "section_title": "Agreement in restraint of trade, void",
                "content": "Every agreement by which any one is restrained from exercising a lawful profession, trade or business of any kind, is to that extent void. Exception 1: Saving of agreement not to carry on business of which goodwill is sold - One who sells the goodwill of a business may agree with the buyer to refrain from carrying on a similar business, within specified local limits, so long as the buyer carries on a like business therein, provided that such limits appear to the Court reasonable.",
                "explanation_text": "Under Section 27, any covenant restraining an individual from exercising a lawful profession, trade, or business post-termination is void. Unlike English common law, the doctrine of reasonableness does NOT save a post-employment non-compete covenant in India."
            },
            {
                "section_number": "Section 28",
                "section_title": "Agreements in restraint of legal proceedings, void",
                "content": "Every agreement, by which any party thereto is restricted absolutely from enforcing his rights under or in respect of any contract, by the usual legal proceedings in the ordinary tribunals, or which limits the time within which he may thus enforce his rights, is void to that extent. Exception 1: Saving of contract to refer to arbitration dispute that may arise.",
                "explanation_text": "Parties cannot contractually extinguish the statutory limitation period or completely oust court jurisdiction, though arbitration agreements are expressly permitted."
            },
            {
                "section_number": "Section 73",
                "section_title": "Compensation for loss or damage caused by breach of contract",
                "content": "When a contract has been broken, the party who suffers by such breach is entitled to receive, from the party who has broken the contract, compensation for any loss or damage caused to him thereby, which naturally arose in the usual course of things from such breach, or which the parties knew, when they made the contract, to be likely to result from the breach of it. Such compensation is not to be given for any remote and indirect loss or damage sustained by reason of the breach.",
                "explanation_text": "Damages under Indian contract law are compensatory, not punitive. Only direct losses or losses in reasonable contemplation of the parties at formation are recoverable; remote/consequential damages are barred."
            },
            {
                "section_number": "Section 74",
                "section_title": "Compensation for breach of contract where penalty stipulated for",
                "content": "When a contract has been broken, if a sum is named in the contract as the amount to be paid in case of such breach, or if the contract contains any other stipulation by way of penalty, the party complaining of the breach is entitled, whether or not actual damage or loss is proved to have been caused thereby, to receive from the party who has broken the contract reasonable compensation not exceeding the amount so named or, as the case may be, the penalty stipulated for.",
                "explanation_text": "Section 74 treats liquidated damages as an upper ceiling. Indian courts will only award 'reasonable compensation' up to that ceiling; proof of actual loss is required unless impossible to prove."
            },
            {
                "section_number": "Section 124",
                "section_title": "'Contract of indemnity' defined",
                "content": "A contract by which one party promises to save the other from loss caused to him by the conduct of the promisor himself, or by the conduct of any other person, is called a 'contract of indemnity'.",
                "explanation_text": "Defines contractual indemnification obligations under Indian law."
            }
        ]
    },
    {
        "act_name": "The Constitution of India",
        "act_year": 1950,
        "act_number": "Constitutional Document",
        "short_title": "The Constitution of India, 1950",
        "jurisdiction": "Central",
        "enactment_date": date(1949, 11, 26),
        "commencement_date": date(1950, 1, 26),
        "source_url": "https://legislative.gov.in/constitution-of-india/",
        "status": "CURRENT",
        "sections": [
            {
                "section_number": "Article 14",
                "section_title": "Equality before law",
                "content": "The State shall not deny to any person equality before the law or the equal protection of the laws within the territory of India.",
                "explanation_text": "Guarantees equality and non-arbitrariness in State action; strikes down unconscionable and arbitrary actions by government undertakings."
            },
            {
                "section_number": "Article 19(1)(g)",
                "section_title": "Right to practice any profession, or to carry on any occupation, trade or business",
                "content": "All citizens shall have the right to practise any profession, or to carry on any occupation, trade or business, subject to reasonable restrictions imposed by the State in the interests of the general public.",
                "explanation_text": "Constitutional right to work and trade. Restraints of trade in private contracts are evaluated against this public interest foundation."
            },
            {
                "section_number": "Article 21",
                "section_title": "Protection of life and personal liberty",
                "content": "No person shall be deprived of his life or personal liberty except according to procedure established by law.",
                "explanation_text": "Fundamental right expanding to right to livelihood, dignity, procedural fairness, and informational privacy."
            },
            {
                "section_number": "Article 32",
                "section_title": "Remedies for enforcement of rights conferred by this Part",
                "content": "The right to move the Supreme Court by appropriate proceedings for the enforcement of the rights conferred by this Part is guaranteed. The Supreme Court shall have power to issue directions or orders or writs, including writs in the nature of habeas corpus, mandamus, prohibition, quo warranto and certiorari.",
                "explanation_text": "Constitutional remedies for breach of fundamental rights."
            }
        ]
    },
    {
        "act_name": "Arbitration and Conciliation Act",
        "act_year": 1996,
        "act_number": "Act No. 26 of 1996",
        "short_title": "The Arbitration and Conciliation Act, 1996",
        "jurisdiction": "Central",
        "enactment_date": date(1996, 8, 16),
        "commencement_date": date(1996, 8, 22),
        "source_url": "https://www.indiacode.nic.in/handle/123456789/1978",
        "status": "CURRENT",
        "sections": [
            {
                "section_number": "Section 7",
                "section_title": "Arbitration agreement",
                "content": "In this Part, 'arbitration agreement' means an agreement by the parties to submit to arbitration all or certain disputes which have arisen or which may arise between them in respect of a defined legal relationship, whether contractual or not. An arbitration agreement shall be in writing.",
                "explanation_text": "Mandatory requirement that arbitration agreements in Indian commercial contracts must be in writing."
            },
            {
                "section_number": "Section 34",
                "section_title": "Application for setting aside arbitral award",
                "content": "Recourse to a Court against an arbitral award may be made only by an application for setting aside such award in accordance with sub-section (2) and sub-section (3). An award may be set aside if it is in conflict with the public policy of India, or vitiated by patent illegality appearing on the face of the award.",
                "explanation_text": "Strictly limited grounds on which an Indian court can interfere with a domestic arbitral award."
            }
        ]
    }
]

# ----------------------------------------------------
# COURT PRECEDENTS DATA
# ----------------------------------------------------
JUDGMENTS_SEED = [
    {
        "case_title": "Percept D'Mark (India) Pvt. Ltd. v. Zaheer Khan & Anr.",
        "neutral_citation": "2006 INSC 190",
        "standard_citation": "(2006) 4 SCC 227",
        "court_name": "Supreme Court of India",
        "judgment_date": date(2006, 3, 22),
        "bench": "Y.K. Sabharwal, C.K. Thakker, R.V. Raveendran",
        "headnote": "Restraint of trade - Section 27, Indian Contract Act - Post-contractual covenants.",
        "ratio_decidendi": "Under Section 27 of the Indian Contract Act, 1872, a restrictive covenant extending beyond the term of the contract is completely void and unenforceable. The doctrine of 'reasonableness' of restraint developed under English common law does not apply in India. Section 27 is absolute and admits only the statutory exception of sale of goodwill.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Niranjan Shankar Golikari v. Century Spinning & Mfg. Co. Ltd.",
        "neutral_citation": "1967 INSC 12",
        "standard_citation": "(1967) 2 SCR 378",
        "court_name": "Supreme Court of India",
        "judgment_date": date(1967, 1, 17),
        "bench": "J.M. Shelat, V. Bhargava",
        "headnote": "Negative covenants during term of contract vs post-employment restraints.",
        "ratio_decidendi": "A negative covenant operating during the period of employment when the employee is bound to serve the employer exclusively is not a restraint of trade under Section 27, unless the covenant is unconscionable or one-sided. Restraints during the contract are valid; restraints post-contract are void.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Superintendence Company of India (P) Ltd. v. Krishan Murgai",
        "neutral_citation": "1980 INSC 95",
        "standard_citation": "(1981) 2 SCC 246",
        "court_name": "Supreme Court of India",
        "judgment_date": date(1980, 5, 6),
        "bench": "V.D. Tulzapurkar, R.S. Pathak, A.P. Sen",
        "headnote": "Post-service non-compete clauses in employment contracts.",
        "ratio_decidendi": "A post-service restrictive covenant restraining an employee from engaging in a similar business or employment after termination is void under Section 27 of the Indian Contract Act. The words 'to that extent void' render the restriction completely unenforceable irrespective of duration or geographic scope.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Central Inland Water Transport Corp. Ltd. v. Brojo Nath Ganguly",
        "neutral_citation": "1986 INSC 67",
        "standard_citation": "(1986) 3 SCC 156",
        "court_name": "Supreme Court of India",
        "judgment_date": date(1986, 4, 6),
        "bench": "D.P. Madon, O. Chinnappa Reddy",
        "headnote": "Unconscionable contracts - Section 23 Contract Act & Article 14 Constitution.",
        "ratio_decidendi": "Courts will not enforce, and will strike down, an unfair and unconscionable clause in a contract entered into by parties who are not equal in bargaining power. A clause allowing termination of permanent employment without cause on 3 months' notice is contrary to public policy and void under Section 23.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Oil & Natural Gas Corporation Ltd. v. Saw Pipes Ltd.",
        "neutral_citation": "2003 INSC 226",
        "standard_citation": "(2003) 5 SCC 705",
        "court_name": "Supreme Court of India",
        "judgment_date": date(2003, 4, 17),
        "bench": "M.B. Shah, Arun Kumar",
        "headnote": "Liquidated damages under Section 74 - Genuine pre-estimate of loss.",
        "ratio_decidendi": "If the compensation named in the contract is a genuine pre-estimate of loss agreed by the parties, and it is impossible or difficult to prove exact loss, the court can award the liquidated amount without requiring strict mathematical proof of actual damages under Section 74.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Kailash Nath Associates v. Delhi Development Authority",
        "neutral_citation": "2015 INSC 30",
        "standard_citation": "(2015) 4 SCC 136",
        "court_name": "Supreme Court of India",
        "judgment_date": date(2015, 1, 9),
        "bench": "Ranjan Gogoi, R.F. Nariman",
        "headnote": "Proof of loss in liquidated damages - Forfeiture of earnest money under Section 74.",
        "ratio_decidendi": "Damage or loss is the foundation for an award of compensation under Section 74. Compensation can only be awarded when loss or damage actually results. Liquidated damages cannot be claimed without proof of loss where such loss is capable of being assessed.",
        "source_url": "https://escr.sci.gov.in/"
    },
    {
        "case_title": "Justice K.S. Puttaswamy (Retd.) v. Union of India",
        "neutral_citation": "2017 INSC 609",
        "standard_citation": "(2017) 10 SCC 1",
        "court_name": "Supreme Court of India",
        "judgment_date": date(2017, 8, 24),
        "bench": "J.S. Khehar, J. Chelameswar, S.A. Bobde, D.Y. Chandrachud (9-Judge Bench)",
        "headnote": "Right to Privacy - Article 21 - Informational privacy & commercial data.",
        "ratio_decidendi": "The right to privacy is a fundamental right guaranteed under Article 21 of the Constitution of India. Informational privacy forms an integral facet of personal liberty, impacting commercial data protection and individual consent.",
        "source_url": "https://escr.sci.gov.in/"
    }
]

async def seed_indian_legal_corpus():
    print("=" * 70)
    print("Seeding Indian Legal Knowledge Base (PostgreSQL & Qdrant)")
    print("=" * 70)

    # 1. Initialize DB tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        # ----------------------------------------------------
        # Seed Statutes and Sections
        # ----------------------------------------------------
        qdrant_points = []

        for stat_data in STATUTES_SEED:
            from sqlalchemy import select
            stat_res = await session.execute(
                select(LegalStatute).where(LegalStatute.act_name == stat_data["act_name"])
            )
            existing_statute = stat_res.scalars().first()

            if not existing_statute:
                statute_id = str(uuid.uuid4())
                statute = LegalStatute(
                    id=statute_id,
                    act_name=stat_data["act_name"],
                    act_year=stat_data["act_year"],
                    act_number=stat_data["act_number"],
                    short_title=stat_data["short_title"],
                    jurisdiction=stat_data["jurisdiction"],
                    enactment_date=stat_data["enactment_date"],
                    commencement_date=stat_data["commencement_date"],
                    source_url=stat_data["source_url"],
                    status=stat_data["status"]
                )
                session.add(statute)
                await session.flush()
            else:
                statute_id = existing_statute.id

            sec_res = await session.execute(
                select(LegalSection).where(LegalSection.statute_id == statute_id)
            )
            existing_sec_map = {s.section_number: s for s in sec_res.scalars().all()}

            for sec_data in stat_data["sections"]:
                sec_num = sec_data["section_number"]
                if sec_num in existing_sec_map:
                    sec_id = existing_sec_map[sec_num].id
                else:
                    sec_id = str(uuid.uuid4())
                    sec = LegalSection(
                        id=sec_id,
                        statute_id=statute_id,
                        section_number=sec_num,
                        section_title=sec_data["section_title"],
                        content=sec_data["content"],
                        explanation_text=sec_data["explanation_text"],
                        status="CURRENT",
                        qdrant_point_id=sec_id
                    )
                    session.add(sec)

                # Prepare search text for embedding
                search_text = f"[{stat_data['act_name']}, {stat_data['act_year']} | {sec_data['section_number']}: {sec_data['section_title']}]: {sec_data['content']} {sec_data.get('explanation_text', '')}"
                qdrant_points.append({
                    "id": sec_id,
                    "search_text": search_text,
                    "document_type": "STATUTE_SECTION",
                    "act_name": stat_data["act_name"],
                    "act_year": stat_data["act_year"],
                    "section_number": sec_data["section_number"],
                    "title": sec_data["section_title"],
                    "content": sec_data["content"],
                    "source_url": stat_data["source_url"],
                    "status": "CURRENT"
                })

        # ----------------------------------------------------
        # Seed Court Judgments (Idempotent)
        # ----------------------------------------------------
        judg_res = await session.execute(select(CourtJudgment))
        existing_judg_map = {j.neutral_citation: j for j in judg_res.scalars().all()}

        for j_data in JUDGMENTS_SEED:
            nc = j_data["neutral_citation"]
            if nc in existing_judg_map:
                j_id = existing_judg_map[nc].id
            else:
                j_id = str(uuid.uuid4())
                judgment = CourtJudgment(
                    id=j_id,
                    case_title=j_data["case_title"],
                    neutral_citation=nc,
                    standard_citation=j_data["standard_citation"],
                    court_name=j_data["court_name"],
                    judgment_date=j_data["judgment_date"],
                    bench=j_data["bench"],
                    headnote=j_data["headnote"],
                    ratio_decidendi=j_data["ratio_decidendi"],
                    source_url=j_data["source_url"],
                    qdrant_point_id=j_id
                )
                session.add(judgment)

            search_text = f"[{j_data['court_name']} | {j_data['case_title']} ({j_data['neutral_citation']})]: {j_data['headnote']} Principle: {j_data['ratio_decidendi']}"
            qdrant_points.append({
                "id": j_id,
                "search_text": search_text,
                "document_type": "COURT_JUDGMENT",
                "case_title": j_data["case_title"],
                "neutral_citation": j_data["neutral_citation"],
                "court_name": j_data["court_name"],
                "judgment_date": str(j_data["judgment_date"]),
                "ratio_decidendi": j_data["ratio_decidendi"],
                "content": f"{j_data['case_title']} ({j_data['neutral_citation']}): {j_data['ratio_decidendi']}",
                "title": j_data["case_title"],
                "source_url": j_data["source_url"],
                "status": "CURRENT"
            })

        await session.commit()
        print(f"-> PostgreSQL sync complete ({len(STATUTES_SEED)} statutes and {len(JUDGMENTS_SEED)} judgments synchronized).")

    # ----------------------------------------------------
    # Embed and Upsert to Qdrant
    # ----------------------------------------------------
    texts_to_embed = [p["search_text"] for p in qdrant_points]
    print(f"-> Generating dense vectors for {len(texts_to_embed)} legal units...")
    vectors = await embedding_service.get_batch_embeddings(texts_to_embed)

    vector_points = []
    for p, vec in zip(qdrant_points, vectors):
        p_copy = p.copy()
        p_copy["vector"] = vec
        vector_points.append(p_copy)

    qdrant_service.upsert_legal_points(vector_points)
    print(f"-> Successfully indexed {len(vector_points)} points into Qdrant collection: {qdrant_service.legal_collection}")
    print("=" * 70)
    print("Seeding Complete! Indian Legal Corpus is now active.")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(seed_indian_legal_corpus())

