"""Create the FastAPI application and make it available to the local frontend."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.analysis import router as analysis_router

app = FastAPI(title="CodeGuard AI API")

# The frontend is served on its own local port, so the browser needs CORS permission.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500", "null"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(analysis_router)


@app.get("/")
def health_check() -> dict[str, str]:
    """Report that the API process is running."""
    return {"status": "ok", "message": "CodeGuard AI API is running"}
