# backend/app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import router as apirouter

app = FastAPI(title="Outdaxius API")

# Read allowed origins from env var, comma-separated, falling back to local dev
origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

class CORSErrorFixMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
        except Exception as e:
            response = JSONResponse({"detail": str(e)}, status_code=500)
        return response

app.add_middleware(CORSErrorFixMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(apirouter, prefix="/api")

@app.get("/health")
def health():
    return {"status": "ok"}