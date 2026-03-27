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

@router.get("/download")
async def download_video(url: str, title: str = "video", ext: str = "mp4"):
    """
    Proxy endpoint to download a video directly as an attachment.
    This solves CORS issues and forces a file download instead of playing in-browser.
    """
    import urllib.request
    from fastapi.responses import StreamingResponse
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req)
        def iterfile():
            while True:
                chunk = response.read(8192 * 4) # 32KB chunks
                if not chunk:
                    break
                yield chunk
        import urllib.parse
        encoded_title = urllib.parse.quote(title)
        headers = {
            'Content-Disposition': f"attachment; filename*=utf-8''{encoded_title}.{ext}"
        }
        return StreamingResponse(iterfile(), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        logger.error(f"Error proxying download: {e}")
        raise HTTPException(status_code=400, detail=str(e))
