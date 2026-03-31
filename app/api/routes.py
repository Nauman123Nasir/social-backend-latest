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
    import urllib.parse
    from fastapi.responses import StreamingResponse
    
    try:
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise HTTPException(status_code=403, detail="URL scheme not allowed. Only HTTP/HTTPS are supported.")
            
        hostname = (parsed_url.hostname or "").lower()
        forbidden_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
        
        # Block private and loopback networks to prevent internal SSRF
        if (hostname in forbidden_hosts or 
            hostname.startswith("169.254.") or 
            hostname.startswith("10.") or 
            hostname.startswith("192.168.") or 
            hostname.startswith("172.")):
            raise HTTPException(status_code=403, detail="Target host is strictly forbidden by security policy.")

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
