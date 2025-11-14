from fastapi import APIRouter, Query
from pydantic import BaseModel
from services.memory_manager import MemoryManager

router = APIRouter()
mm = MemoryManager()


class MemoryItem(BaseModel):
    user_id: str
    text: str
    url: str | None = None
    title: str | None = None


@router.post("/add", tags=["memory"])
async def add_memory(item: MemoryItem):
    id_ = await mm.upsert_text(
        item.user_id, item.text, item.url or "", item.title or ""
    )
    return {"id": id_}


@router.get("/search", tags=["memory"])
async def search_memory(user_id: str = Query(...), q: str = Query(...)):
    results = await mm.search(user_id=user_id, query=q)
    return {"matches": results}
