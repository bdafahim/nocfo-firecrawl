from fastapi import FastAPI
from .db import engine, Base
from .routes.firecrawl_webhook import router as firecrawl_router

app = FastAPI(title="NoCFO Firecrawl Ingest")

# Create tables (local/dev convenience)
Base.metadata.create_all(bind=engine)

app.include_router(firecrawl_router)

@app.get("/health")
def health():
    return {"ok": True}
