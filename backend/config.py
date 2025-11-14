import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()  # Reads from .env file in backend/


@dataclass
class Settings:
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
    api_version: str = "0.1.0"
    pinecone_api_key: str = os.getenv("PINECONE_API_KEY", "")
    pinecone_index: str = os.getenv("PINECONE_INDEX", "sira-vectors")


settings = Settings()
