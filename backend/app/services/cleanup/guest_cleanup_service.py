import os
import time
import logging
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.models import Contract
from app.services.vector_store.qdrant_client import qdrant_service
from app.services.storage.cloudinary_service import cloudinary_service

logger = logging.getLogger("contract_cleanup")

class GuestCleanupService:
    """
    Automated background cleanup service for expired temporary guest contracts.
    
    Guarantees:
    1. NEVER touches authenticated user contracts.
    2. Idempotent resource deletion across Qdrant, Cloudinary, DB, and local disk.
    3. Failure tracking with automatic retry limits.
    4. Structured audit logging for all deletions.
    """

    MAX_RETRIES = 3

    async def run_cleanup(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Scans for expired guest contracts and purges associated resources.
        Returns a summary report of cleaned contracts and any partial failures.
        """
        start_time = time.time()
        now = datetime.utcnow()

        # Strict safety query: MUST BE guest AND expired AND retry count not exceeded
        query = select(Contract).where(
            and_(
                Contract.is_guest == True,
                Contract.user_id.is_(None),  # Secondary safety check: NEVER touch user-owned contracts
                Contract.expires_at.is_not(None),
                Contract.expires_at <= now,
                Contract.cleanup_status != "CLEANED",
                Contract.cleanup_retries < self.MAX_RETRIES
            )
        )
        result = await db.execute(query)
        expired_contracts: List[Contract] = result.scalars().all()

        report = {
            "scanned_at": now.isoformat(),
            "expired_found": len(expired_contracts),
            "successfully_cleaned": 0,
            "failed_count": 0,
            "cleaned_contracts": [],
            "duration_ms": 0.0
        }

        if not expired_contracts:
            logger.debug("Guest cleanup job: no expired contracts found.")
            report["duration_ms"] = round((time.time() - start_time) * 1000, 2)
            return report

        logger.info(f"Guest cleanup job started. Processing {len(expired_contracts)} expired contracts...")

        for contract in expired_contracts:
            contract_id = contract.id
            guest_session = contract.guest_session_id
            filename = contract.filename
            public_id = contract.cloudinary_public_id

            qdrant_ok = True
            cloudinary_ok = True
            local_ok = True

            # 1. Purge vectors from Qdrant
            try:
                qdrant_ok = qdrant_service.delete_contract_points(contract_id)
            except Exception as e:
                logger.error(f"[CLEANUP ERROR] Failed to purge Qdrant vectors for contract {contract_id}: {e}")
                qdrant_ok = False

            # 2. Purge asset from Cloudinary
            if public_id:
                try:
                    cloudinary_ok = await cloudinary_service.delete_file(public_id=public_id, resource_type="raw")
                except Exception as e:
                    logger.error(f"[CLEANUP ERROR] Failed to delete Cloudinary asset {public_id}: {e}")
                    cloudinary_ok = False

            # 3. Purge local temporary file if present
            if contract.file_path and os.path.exists(contract.file_path):
                try:
                    os.remove(contract.file_path)
                    logger.info(f"[CLEANUP] Deleted local file {contract.file_path}")
                except Exception as e:
                    logger.warning(f"[CLEANUP] Failed to remove local file {contract.file_path}: {e}")
                    local_ok = False

            # 4. Handle status & database record
            if qdrant_ok and cloudinary_ok:
                # All external assets confirmed removed - safe to delete DB record
                await db.delete(contract)
                await db.commit()
                report["successfully_cleaned"] += 1
                report["cleaned_contracts"].append({
                    "contract_id": contract_id,
                    "filename": filename,
                    "guest_session": guest_session,
                    "status": "PURGED"
                })
                logger.info(
                    f"[CLEANUP AUDIT] Successfully purged expired guest contract "
                    f"id={contract_id} filename='{filename}' session={guest_session} "
                    f"(Qdrant: ok, Cloudinary: ok, Local: {local_ok})"
                )
            else:
                # Track partial failure for idempotent retry
                contract.cleanup_retries += 1
                if not qdrant_ok:
                    contract.cleanup_status = "FAILED_QDRANT"
                elif not cloudinary_ok:
                    contract.cleanup_status = "FAILED_CLOUDINARY"
                await db.commit()
                report["failed_count"] += 1
                logger.warning(
                    f"[CLEANUP RETRY NEEDED] Contract {contract_id} partial failure "
                    f"(status={contract.cleanup_status}, retries={contract.cleanup_retries})"
                )

        report["duration_ms"] = round((time.time() - start_time) * 1000, 2)
        logger.info(f"Guest cleanup job completed in {report['duration_ms']}ms. Purged: {report['successfully_cleaned']}, Failed: {report['failed_count']}.")
        return report

guest_cleanup_service = GuestCleanupService()

