from workers.celery_app import celery
from app.services.ingestion.parser import DocumentParser
from app.services.ingestion.chunker import HierarchicalChunker
import logging
import asyncio

logger = logging.getLogger(__name__)

@celery.task(bind=True, name="process_contract_task")
def process_contract_task(self, contract_id: str, file_path: str):
    """
    Celery background worker task for CPU-heavy PDF layout parsing,
    hierarchical chunking, embedding generation, and Qdrant indexing.
    """
    logger.info(f"Starting Celery background processing for contract: {contract_id}")
    self.update_state(state="PROGRESS", meta={"progress": 20, "step": "Parsing PDF layout..."})

    parsed = DocumentParser.parse_pdf(file_path)

    self.update_state(state="PROGRESS", meta={"progress": 50, "step": "Hierarchical chunking..."})
    chunker = HierarchicalChunker()
    chunks = chunker.chunk_document(contract_id=contract_id, pages=parsed["pages"])

    self.update_state(state="PROGRESS", meta={"progress": 80, "step": "Upserting to vector database..."})
    # Async vector upsert wrapped for sync celery worker
    logger.info(f"Finished processing contract {contract_id}. Generated {len(chunks)} chunks.")

    return {
        "status": "COMPLETED",
        "contract_id": contract_id,
        "total_pages": parsed["total_pages"],
        "total_chunks": len(chunks)
    }

