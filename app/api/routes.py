from fastapi import APIRouter, HTTPException
from app.models.schemas import VideoInfoRequest, VideoInfoResponse
from app.services.downloader import downloader_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/info", response_model=VideoInfoResponse)
async def get_video_info(request: VideoInfoRequest):
    """
    Endpoint to trigger video metadata extraction.
    Takes a social media URL and returns available video formats.
    """
    try:
        logger.info(f"Extracting info for {request.url}")
        info = downloader_service.get_video_info(str(request.url))
        return VideoInfoResponse(**info)
    except Exception as e:
        logger.error(f"Error extracting info: {e}")
        raise HTTPException(status_code=400, detail=str(e))
