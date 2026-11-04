from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import yaml
import os

from app.db.session import get_db
from app.db.models import Playbook
from app.schemas.playbook import PlaybookCreate, PlaybookResponse

router = APIRouter()

PLAYBOOK_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../playbooks"))

def load_local_playbooks():
    playbooks = []
    if os.path.exists(PLAYBOOK_DIR):
        for file in os.listdir(PLAYBOOK_DIR):
            if file.endswith((".yaml", ".yml")):
                path = os.path.join(PLAYBOOK_DIR, file)
                with open(path, "r") as f:
                    data = yaml.safe_load(f)
                    data["id"] = file.replace(".yaml", "").replace(".yml", "")
                    playbooks.append(data)
    return playbooks

@router.get("", response_model=List[dict])
async def list_playbooks(db: AsyncSession = Depends(get_db)):
    # Load default file-based playbooks
    playbooks = load_local_playbooks()

    # Load custom DB playbooks
    db_res = await db.execute(select(Playbook))
    for p in db_res.scalars().all():
        playbooks.append({
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "rules": p.rules_json,
            "is_default": p.is_default
        })
    return playbooks

@router.post("", response_model=PlaybookResponse)
async def create_playbook(payload: PlaybookCreate, db: AsyncSession = Depends(get_db)):
    rules_dict = [r.model_dump() for r in payload.rules]
    playbook = Playbook(
        name=payload.name,
        description=payload.description,
        rules_json=rules_dict,
        is_default=payload.is_default
    )
    db.add(playbook)
    await db.commit()
    await db.refresh(playbook)
    return playbook

