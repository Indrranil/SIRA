from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import health, research, memory

app = FastAPI(title="SIRA Backend", version=settings.api_version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/health")
app.include_router(research.router, prefix="/api/pipeline")
app.include_router(memory.router, prefix="/api/memory")

@app.get("/")
def root():
    return {"service": "SIRA", "version": settings.api_version}

