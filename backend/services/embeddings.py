from sentence_transformers import SentenceTransformer
from functools import lru_cache


@lru_cache(maxsize=1)
def get_embedder():
    return SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    model = get_embedder()
    return model.encode([text], normalize_embeddings=True)[0].tolist()
