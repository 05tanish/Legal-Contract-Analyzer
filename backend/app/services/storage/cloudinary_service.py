import os
import asyncio
import logging
from typing import Optional
import cloudinary
import cloudinary.uploader
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class CloudinaryService:
    def __init__(self):
        self._is_initialized = False

    def _ensure_configured(self) -> bool:
        """Initializes Cloudinary credentials from app settings."""
        if not self._is_initialized:
            if (
                settings.CLOUDINARY_CLOUD_NAME and
                settings.CLOUDINARY_API_KEY and
                settings.CLOUDINARY_API_SECRET
            ):
                cloudinary.config(
                    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
                    api_key=settings.CLOUDINARY_API_KEY,
                    api_secret=settings.CLOUDINARY_API_SECRET,
                    secure=True
                )
                self._is_initialized = True
                logger.info(f"Cloudinary initialized for cloud: {settings.CLOUDINARY_CLOUD_NAME}")
            else:
                logger.debug("Cloudinary credentials not fully configured.")
        return self._is_initialized

    def is_configured(self) -> bool:
        """Returns True if Cloudinary credentials are provided and valid."""
        return self._ensure_configured()

    async def upload_file(
        self,
        file_path: str,
        public_id: Optional[str] = None,
        folder: str = "contracts"
    ) -> Optional[str]:
        """
        Uploads a PDF or legal document to Cloudinary.
        Runs asynchronously in thread pool so it does not block the FastAPI event loop.
        Returns the secure HTTPS URL on success, or None on failure.
        """
        if not self._ensure_configured():
            logger.warning("Cloudinary is not configured. Skipping cloud upload.")
            return None

        if not os.path.exists(file_path):
            logger.error(f"Cannot upload to Cloudinary: file does not exist at {file_path}")
            return None

        try:
            # Cloudinary raw upload preserves exact PDF format and checksum
            upload_kwargs = {
                "folder": folder,
                "resource_type": "raw",
                "use_filename": True,
                "unique_filename": True,
            }
            if public_id:
                upload_kwargs["public_id"] = public_id

            logger.info(f"Uploading '{os.path.basename(file_path)}' to Cloudinary folder '{folder}'...")
            
            # Execute synchronous SDK call in thread
            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                file_path,
                **upload_kwargs
            )

            secure_url = result.get("secure_url")
            assigned_public_id = result.get("public_id")
            logger.info(f"Successfully uploaded to Cloudinary: {secure_url} (public_id: {assigned_public_id})")
            return secure_url

        except Exception as e:
            logger.error(f"Cloudinary upload failed for '{file_path}': {e}. Falling back to local storage.")
            return None

    async def upload_document(
        self,
        file_path: str,
        public_id: Optional[str] = None,
        folder: str = "contracts"
    ) -> Optional[dict]:
        """
        Uploads document and returns dict containing both 'secure_url' and 'public_id'.
        """
        if not self._ensure_configured():
            return None
        if not os.path.exists(file_path):
            return None
        try:
            upload_kwargs = {
                "folder": folder,
                "resource_type": "raw",
                "use_filename": True,
                "unique_filename": True,
            }
            if public_id:
                upload_kwargs["public_id"] = public_id

            result = await asyncio.to_thread(
                cloudinary.uploader.upload,
                file_path,
                **upload_kwargs
            )
            return {
                "secure_url": result.get("secure_url"),
                "public_id": result.get("public_id")
            }
        except Exception as e:
            logger.error(f"Cloudinary document upload failed: {e}")
            return None

    async def delete_file(self, public_id: str, resource_type: str = "raw") -> bool:
        """
        Deletes a document from Cloudinary by its public_id.
        Runs asynchronously in a thread pool. Idempotent: returns True if deleted or already not found.
        """
        if not self._ensure_configured():
            logger.warning("Cloudinary not configured. Skipping remote deletion.")
            return True

        try:
            logger.info(f"Deleting asset '{public_id}' (resource_type={resource_type}) from Cloudinary...")
            result = await asyncio.to_thread(
                cloudinary.uploader.destroy,
                public_id,
                resource_type=resource_type,
                invalidate=True
            )
            status = result.get("result")
            if status in ("ok", "not found"):
                logger.info(f"Cloudinary delete completed for {public_id}: {status}")
                return True
            else:
                logger.warning(f"Cloudinary destroy returned unexpected status for {public_id}: {status}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file '{public_id}' from Cloudinary: {e}")
            return False

    async def download_file(self, file_url: str, destination_path: str) -> bool:
        """
        Downloads a document from Cloudinary to a local path (for parsing / local caching).
        """
        try:
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(file_url)
                if resp.status_code == 200:
                    with open(destination_path, "wb") as f:
                        f.write(resp.content)
                    logger.info(f"Downloaded contract from Cloudinary to {destination_path}")
                    return True
                else:
                    logger.warning(f"Failed to download from Cloudinary ({resp.status_code}): {file_url}")
                    return False
        except Exception as e:
            logger.error(f"Error downloading file from Cloudinary: {e}")
            return False

cloudinary_service = CloudinaryService()

