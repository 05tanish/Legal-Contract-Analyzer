from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class ContractBase(BaseModel):
    filename: str
    file_size_bytes: int

class ContractCreate(ContractBase):
    file_path: str
    file_hash: str

class ContractChunkRead(BaseModel):
    id: str
    chunk_index: int
    page_number: int
    section_title: Optional[str] = None
    content: str
    is_parent: bool

    model_config = ConfigDict(from_attributes=True)

class ContractResponse(BaseModel):
    id: str
    filename: str
    file_size_bytes: int
    total_pages: int
    contract_type: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ContractDetailResponse(ContractResponse):
    chunks_count: int = 0
    latest_audit_id: Optional[str] = None

