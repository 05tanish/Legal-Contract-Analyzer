from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from typing import List, Optional
from datetime import datetime, timedelta
import os
import re
import uuid
import logging
import aiofiles

from app.core.config import settings
from app.db.session import get_db
from app.db.models import Contract, ContractChunk, User
from app.schemas.contract import ContractResponse, ContractDetailResponse
from app.core.security import (
    security,
    get_current_user_optional,
    get_client_guest_session_id,
    get_user_from_request_or_query,
    validate_contract_access
)
from app.services.ingestion.parser import DocumentParser
from app.services.ingestion.chunker import HierarchicalChunker
from app.services.embedding.embedder import embedding_service
from app.services.vector_store.qdrant_client import qdrant_service
from app.services.storage.cloudinary_service import cloudinary_service
from app.services.clause_detection.detector import clause_detector

logger = logging.getLogger(__name__)

# High-performance in-memory metadata cache to eliminate Neon DB query delays on static PDF streaming
_contract_cache: dict = {}

router = APIRouter()

@router.post("/upload", response_model=ContractResponse)
async def upload_contract(
    request: Request,
    file: UploadFile = File(...),
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Unified Contract Ingestion Endpoint:
    - If user is authenticated: associates contract with user, permanent retention.
    - If user is guest: assigns temporary session ID and TTL (expires_at).
    - Stores PDF in Cloudinary and chunks in relational DB & Qdrant.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Please select a valid PDF file. Other file types are not currently supported."
        )

    # 1. Determine user identity & session
    current_user: Optional[User] = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)
    if not current_user and not guest_session_id:
        guest_session_id = str(uuid.uuid4())

    is_guest_upload = current_user is None
    expires_at = (
        datetime.utcnow() + timedelta(hours=settings.GUEST_CONTRACT_RETENTION_HOURS)
        if is_guest_upload else None
    )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    # Sanitize filename to avoid path traversal and special char issues
    safe_filename = re.sub(r'[^a-zA-Z0-9_.\-]', '_', file.filename)
    file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, safe_filename))

    # Read file bytes once into memory
    content = await file.read()

    # Save uploaded file locally
    async with aiofiles.open(file_path, "wb") as buffer:
        await buffer.write(content)

    # 2. Parse document structure using layout-aware parser
    try:
        parsed_doc = DocumentParser.parse_pdf(file_path)
    except Exception as e:
        logger.error(f"Error parsing PDF {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail="We were unable to read this PDF document. Please make sure the file is not password-protected or corrupted."
        )

    # 3. Create Contract DB record (status=PROCESSING until fully saved)
    contract = Contract(
        filename=file.filename,
        file_path=file_path,
        file_hash=parsed_doc["file_hash"],
        file_size_bytes=parsed_doc["file_size_bytes"],
        total_pages=parsed_doc["total_pages"],
        status="PROCESSING",
        is_guest=is_guest_upload,
        user_id=current_user.id if current_user else None,
        guest_session_id=guest_session_id if is_guest_upload else None,
        expires_at=expires_at
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    # 4. Cloudinary upload FIRST - before heavy embedding so PDF is persisted
    #    even if the container gets OOM-killed during embedding.
    try:
        clean_name = re.sub(r'[^a-zA-Z0-9_.\-]', '_', file.filename)
        public_id = f"{contract.id}_{os.path.splitext(clean_name)[0]}"
        cloud_info = await cloudinary_service.upload_document(
            file_path=file_path,
            public_id=public_id,
            folder="guest_contracts" if is_guest_upload else "contracts"
        )
        if cloud_info:
            contract.cloudinary_url = cloud_info.get("secure_url")
            contract.cloudinary_public_id = cloud_info.get("public_id")
            await db.commit()
            logger.info(f"Contract {contract.id} stored in Cloudinary: {contract.cloudinary_url}")
    except Exception as e:
        logger.warning(f"Cloudinary upload non-blocking note: {e}")

    # 5. Chunk document using Hierarchical Chunker
    chunker = HierarchicalChunker()
    chunks_data = chunker.chunk_document(contract_id=contract.id, pages=parsed_doc["pages"])

    # 6. Embed child chunks & upsert to Qdrant (non-fatal - contract saves READY regardless)
    try:
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
            logger.info(f"Indexed {len(qdrant_points)} vectors into Qdrant for contract {contract.id}")
    except Exception as e:
        logger.error(f"Non-fatal: embedding/Qdrant failed for {contract.id}: {e}. Contract still saved.")

    # 7. Save chunk records to relational DB
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

    # Cache metadata for instant PDF streaming
    _contract_cache[contract.id] = {
        "file_path": file_path,
        "user_id": contract.user_id,
        "is_guest": contract.is_guest,
        "guest_session_id": contract.guest_session_id,
        "expires_at": contract.expires_at,
        "cloudinary_url": contract.cloudinary_url,
        "filename": contract.filename
    }

    return contract


@router.get("", response_model=List[ContractResponse])
async def list_contracts(
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists contracts strictly scoped to the authenticated user.
    Without sign-in, returns empty list [] to guarantee no history leaks.
    """
    current_user: Optional[User] = await get_current_user_optional(auth, db)
    if not current_user:
        return []

    result = await db.execute(
        select(Contract)
        .where(Contract.user_id == current_user.id)
        .order_by(Contract.created_at.desc())
    )
    return result.scalars().all()

@router.get("/{contract_id}", response_model=ContractDetailResponse)
async def get_contract(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Retrieves contract metadata with ownership validation."""
    current_user = await get_user_from_request_or_query(request, db)
    if not current_user:
        current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    # Validate ownership & guest TTL
    validate_contract_access(contract, current_user, guest_session_id)

    # Populate cache for future instant access
    _contract_cache[contract.id] = {
        "file_path": contract.file_path,
        "user_id": contract.user_id,
        "is_guest": contract.is_guest,
        "guest_session_id": contract.guest_session_id,
        "expires_at": contract.expires_at,
        "cloudinary_url": contract.cloudinary_url,
        "filename": contract.filename
    }

    chunks_res = await db.execute(select(ContractChunk).where(ContractChunk.contract_id == contract_id))
    chunks_count = len(chunks_res.scalars().all())

    data = ContractDetailResponse.model_validate(contract)
    data.chunks_count = chunks_count
    return data

@router.api_route("/{contract_id}/pdf", methods=["GET", "HEAD"])
async def get_contract_pdf(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Streams contract PDF with IDOR protection and in-memory cache for instant loading."""
    current_user = await get_user_from_request_or_query(request, db)
    if not current_user:
        current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    # 1. Check in-memory cache for near-instant 0ms response
    cached = _contract_cache.get(contract_id)
    if cached:
        from app.db.models import Contract as ContractModel
        fake_contract = ContractModel(
            id=contract_id,
            user_id=cached.get("user_id"),
            is_guest=cached.get("is_guest", False),
            guest_session_id=cached.get("guest_session_id"),
            expires_at=cached.get("expires_at"),
            file_path=cached.get("file_path"),
            cloudinary_url=cached.get("cloudinary_url"),
            filename=cached.get("filename", "contract.pdf")
        )
        validate_contract_access(fake_contract, current_user, guest_session_id)
        cached_file = cached.get("file_path")
        cached_name = cached.get("filename", "contract.pdf")
        cached_cloudinary = cached.get("cloudinary_url")
        if cached_file and os.path.exists(cached_file):
            return FileResponse(
                cached_file,
                media_type="application/pdf",
                filename=cached_name,
                content_disposition_type="inline",
                headers={
                    "Cache-Control": "private, max-age=3600",
                    "Content-Disposition": f'inline; filename="{cached_name}"',
                    "X-Content-Type-Options": "nosniff"
                }
            )
        elif cached_cloudinary:
            # Local file missing (container restart) — redirect to Cloudinary instantly
            return RedirectResponse(url=cached_cloudinary, status_code=302)
        # else fall through to DB query below

    # 2. Query DB if not cached
    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    # Validate access & TTL
    validate_contract_access(contract, current_user, guest_session_id)

    file_path = contract.file_path
    # Try to resolve local file path first
    if not os.path.exists(file_path):
        basename = os.path.basename(file_path)
        candidates = [
            os.path.join(settings.UPLOAD_DIR, basename),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads", basename)),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads", basename)),
        ]
        found_local = False
        for cand in candidates:
            if os.path.exists(cand):
                file_path = cand
                found_local = True
                break
        # If file is not on disk, redirect instantly to Cloudinary (no slow download)
        if not found_local:
            if contract.cloudinary_url:
                logger.info(f"Local file missing for {contract.id}, redirecting to Cloudinary")
                return RedirectResponse(url=contract.cloudinary_url, status_code=302)
            else:
                raise HTTPException(status_code=404, detail="The requested document file could not be found. Please re-upload the contract.")

    # Update cache
    _contract_cache[contract.id] = {
        "file_path": file_path,
        "user_id": contract.user_id,
        "is_guest": contract.is_guest,
        "guest_session_id": contract.guest_session_id,
        "expires_at": contract.expires_at,
        "cloudinary_url": contract.cloudinary_url,
        "filename": contract.filename
    }

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=contract.filename or "contract.pdf",
        content_disposition_type="inline",
        headers={
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f'inline; filename="{contract.filename or "contract.pdf"}"',
            "X-Content-Type-Options": "nosniff"
        }
    )


@router.post("/{contract_id}/detect-clauses")
async def detect_contract_clauses(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Lightweight Cause / Clause Detection Endpoint:
    Available to BOTH Guest and Authenticated users!
    Uses pre-trained NLP / CUAD model for instantaneous, zero-LLM-cost clause classification.
    """
    current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    validate_contract_access(contract, current_user, guest_session_id)

    # Fetch chunks
    chunks_res = await db.execute(
        select(ContractChunk)
        .where(ContractChunk.contract_id == contract_id)
        .order_by(ContractChunk.chunk_index.asc())
    )
    chunks = chunks_res.scalars().all()

    chunks_data = [
        {
            "id": c.id,
            "page_number": c.page_number,
            "section_title": c.section_title,
            "content": c.content,
        }
        for c in chunks if not c.is_parent
    ]

    detected = clause_detector.detect_clauses_in_chunks(chunks_data)

    return {
        "contract_id": contract.id,
        "filename": contract.filename,
        "total_clauses_detected": len(detected),
        "is_guest": contract.is_guest,
        "expires_at": contract.expires_at.isoformat() if contract.expires_at else None,
        "clauses": detected
    }

@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Deletes contract and permanently removes all resources:
    - Purges Qdrant vector points
    - Purges Cloudinary original asset
    - Purges local file
    - Purges database records (cascading to chunks, reports, findings)
    """
    current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")

    validate_contract_access(contract, current_user, guest_session_id)

    # 1. Qdrant vectors deletion
    qdrant_deleted = qdrant_service.delete_contract_points(contract_id)

    # 2. Cloudinary deletion
    cloud_deleted = True
    if contract.cloudinary_public_id:
        cloud_deleted = await cloudinary_service.delete_file(
            public_id=contract.cloudinary_public_id,
            resource_type="raw"
        )

    # 3. Local file deletion
    if contract.file_path and os.path.exists(contract.file_path):
        try:
            os.remove(contract.file_path)
        except Exception as e:
            logger.warning(f"Failed to remove local file {contract.file_path}: {e}")

    # 4. Database deletion
    await db.delete(contract)
    await db.commit()

    # 5. Clear from in-memory cache
    _contract_cache.pop(contract_id, None)

    logger.info(f"Contract {contract_id} permanently deleted (Qdrant: {qdrant_deleted}, Cloudinary: {cloud_deleted}).")

    return {
        "success": True,
        "message": "Contract and all associated resources permanently deleted.",
        "contract_id": contract_id
    }

@router.post("/{contract_id}/reindex", response_model=ContractDetailResponse)
async def reindex_contract(
    contract_id: str,
    request: Request,
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Re-parses, re-chunks, re-embeds, and re-indexes an uploaded contract."""
    current_user = await get_current_user_optional(auth, db)
    guest_session_id = get_client_guest_session_id(request)

    result = await db.execute(select(Contract).where(Contract.id == contract_id))
    contract = result.scalars().first()
    if not contract:
        raise HTTPException(status_code=404, detail="We could not find the requested contract document.")

    validate_contract_access(contract, current_user, guest_session_id)

    file_path = contract.file_path
    if not os.path.exists(file_path):
        basename = os.path.basename(file_path)
        candidates = [
            os.path.join(settings.UPLOAD_DIR, basename),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../uploads", basename)),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "../../uploads", basename)),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                file_path = cand
                break
        else:
            if contract.cloudinary_url:
                local_cache = os.path.join(settings.UPLOAD_DIR, f"{contract.id}_{contract.filename}")
                await cloudinary_service.download_file(contract.cloudinary_url, local_cache)
                if os.path.exists(local_cache):
                    file_path = local_cache
                else:
                    raise HTTPException(status_code=404, detail="Unable to retrieve the document copy from secure storage. Please try again.")
            else:
                raise HTTPException(status_code=404, detail="The requested document file could not be found.")

    # 1. Parse
    parsed_doc = DocumentParser.parse_pdf(file_path)
    chunker = HierarchicalChunker()
    chunks_data = chunker.chunk_document(contract_id=contract.id, pages=parsed_doc["pages"])

    # 2. Delete existing DB chunks
    await db.execute(delete(ContractChunk).where(ContractChunk.contract_id == contract.id))
    await db.commit()

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

    # 4. Save to DB
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
    contract.total_pages = parsed_doc["total_pages"]
    await db.commit()
    await db.refresh(contract)

    data = ContractDetailResponse.model_validate(contract)
    data.chunks_count = len(db_chunks)
    return data
