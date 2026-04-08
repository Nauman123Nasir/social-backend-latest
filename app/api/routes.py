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
async def download_video(
    url: str, 
    title: str = "video", 
    ext: str = "mp4", 
    needs_merging: bool = False, 
    original_url: str = ""
):
    """
    Proxy endpoint to download a video directly as an attachment.
    Supports FFmpeg merging for high-quality video-only streams.
    """
    import urllib.request
    import urllib.parse
    import subprocess
    from fastapi.responses import StreamingResponse

    # CASE 1: High Quality Merging (Needs FFmpeg)
    if needs_merging and original_url:
        try:
            logger.info(f"Starting smart merged download for: {original_url}")
            
            # yt-dlp command to merge best video and best audio and stream to stdout
            cmd = [
                "yt-dlp",
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", "-",
                original_url
            ]
            
            if downloader_service.ydl_opts.get('cookiefile'):
                cmd.extend(["--cookies", downloader_service.ydl_opts['cookiefile']])

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            def stream_output():
                try:
                    while True:
                        chunk = process.stdout.read(1024 * 32) # 32KB chunks
                        if not chunk:
                            break
                        yield chunk
                finally:
                    process.terminate()

            encoded_title = urllib.parse.quote(title)
            headers = {
                'Content-Disposition': f"attachment; filename*=utf-8''{encoded_title}.mp4"
            }
            return StreamingResponse(stream_output(), media_type="video/mp4", headers=headers)
        except Exception as e:
            logger.error(f"Smart merge failed: {e}. Falling back to standard proxy.")

    # CASE 2: Standard Proxy (Fastest for pre-merged files)
    try:
        parsed_url = urllib.parse.urlparse(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise HTTPException(status_code=403, detail="URL scheme not allowed.")
            
        hostname = (parsed_url.hostname or "").lower()
        forbidden_hosts = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "::1"}
        
        if (hostname in forbidden_hosts or hostname.startswith("10.") or 
            hostname.startswith("192.168.") or hostname.startswith("172.")):
            raise HTTPException(status_code=403, detail="Target host forbidden.")

        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib.request.urlopen(req, timeout=15)
        
        def iterfile():
            while True:
                chunk = response.read(8192 * 4)
                if not chunk:
                    break
                yield chunk

        encoded_title = urllib.parse.quote(title)
        headers = { 'Content-Disposition': f"attachment; filename*=utf-8''{encoded_title}.{ext}" }
        return StreamingResponse(iterfile(), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        logger.error(f"Error proxying download: {e}")
        raise HTTPException(status_code=400, detail=str(e))
