from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
import static_ffmpeg
import logging

logger = logging.getLogger(__name__)

# Add bundled ffmpeg binary to PATH at startup - no system install needed
static_ffmpeg.add_paths()
logger.info("static-ffmpeg paths added to system PATH")

app = FastAPI(title="Social Video Downloader API", description="API for extracting video info from social media platforms")

# Configure CORS for our Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
