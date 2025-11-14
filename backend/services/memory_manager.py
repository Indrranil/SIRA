import asyncio
from typing import Any, Dict, List
from pinecone import Pinecone, ServerlessSpec
from config import settings
from services.embeddings import embed_text

_pc = None
_index = None


def _init_pinecone():
    global _pc, _index
    if _pc and _index:
        return _pc, _index

    _pc = Pinecone(api_key=settings.pinecone_api_key)
    existing = [i["name"] for i in _pc.list_indexes().get("indexes", [])]
    if settings.pinecone_index not in existing:
        _pc.create_index(
            name=settings.pinecone_index,
            dimension=384,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    _index = _pc.Index(settings.pinecone_index)
    return _pc, _index


class MemoryManager:
    def __init__(self):
        _init_pinecone()

    async def upsert_text(
        self, user_id: str, text: str, url: str = "", title: str = ""
    ) -> str:
        vec = await asyncio.to_thread(embed_text, text)
        metadata = {"user_id": user_id, "url": url, "title": title}
        vid = str(abs(hash(user_id + text)))[:18]
        _index.upsert(vectors=[{"id": vid, "values": vec, "metadata": metadata}])
        return vid

    async def search(
        self, user_id: str, query: str, top_k: int = 5
    ) -> List[Dict[str, Any]]:
        qvec = await asyncio.to_thread(embed_text, query)
        res = _index.query(
            vector=qvec,
            top_k=top_k,
            include_metadata=True,
            filter={"user_id": {"$eq": user_id}},
        )
        matches = []
        for m in res.get("matches", []):
            matches.append(
                {
                    "id": m["id"],
                    "score": m.get("score", 0),
                    "metadata": m.get("metadata", {}),
                }
            )
        return matches
