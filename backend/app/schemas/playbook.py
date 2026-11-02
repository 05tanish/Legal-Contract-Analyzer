from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

class PlaybookRuleItem(BaseModel):
    category: str = Field(description="Clause category, e.g., 'Indemnification', 'Limitation of Liability'")
    standard_requirement: str = Field(description="Acceptable contract standard or position")
    unacceptable_triggers: List[str] = Field(default_factory=list, description="Keywords or phrases that trigger high risk")
    severity_if_violated: str = Field(default="HIGH", description="CRITICAL, HIGH, MEDIUM, LOW")
    fallback_recommendation: Optional[str] = Field(None, description="Suggested redline amendment language")

class PlaybookCreate(BaseModel):
    name: str
    description: Optional[str] = None
    rules: List[PlaybookRuleItem]
    is_default: bool = False

class PlaybookResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    rules_json: List[dict]
    is_default: bool

    model_config = ConfigDict(from_attributes=True)

