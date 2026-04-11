from fastapi import APIRouter, HTTPException
from app.models.schemas import VideoInfoRequest, VideoInfoResponse
from app.services.downloader import downloader_service
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/diag")
async def diagnostic():
    """
    Diagnostic endpoint to verify environment setup (FFmpeg, yt-dlp)
    """
    import subprocess
    results = {}
    try:
        ffmpeg_ver = subprocess.check_output(["ffmpeg", "-version"], stderr=subprocess.STDOUT).decode()
        results["ffmpeg"] = ffmpeg_ver.splitlines()[0]
    except Exception as e:
        results["ffmpeg"] = f"Error: {str(e)}"
        
    try:
        ytdlp_ver = subprocess.check_output(["yt-dlp", "--version"], stderr=subprocess.STDOUT).decode()
        results["yt-dlp"] = ytdlp_ver.strip()
    except Exception as e:
        results["yt-dlp"] = f"Error: {str(e)}"

    return results

@router.get("/test-merge")
async def test_merge(url: str):
    """
    Debug endpoint: runs yt-dlp merge to a temp file and returns full logs.
    Usage: /api/test-merge?url=<encoded_instagram_url>
    """
    import subprocess, tempfile, os
    tmp_dir = tempfile.mkdtemp()
    output_path = os.path.join(tmp_dir, "output.mp4")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo+bestaudio/best",
        "--merge-output-format", "mp4",
        "--no-playlist",
        "-o", output_path,
        url
    ]

    if downloader_service.ydl_opts.get('cookiefile'):
        cmd.extend(["--cookies", downloader_service.ydl_opts['cookiefile']])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        file_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-3000:],  # last 3000 chars
            "stderr": result.stderr[-3000:],
            "output_file_exists": os.path.exists(output_path),
            "output_file_size_bytes": file_size,
            "cmd": " ".join(cmd)
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        try:
            if os.path.exists(output_path): os.remove(output_path)
            os.rmdir(tmp_dir)
        except Exception:
            pass

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

@router.get("/download-debug")
async def download_debug(
    url: str = "",
    needs_merging: bool = False,
    original_url: str = ""
):
    """Returns what path the download endpoint would take, for debugging."""
    is_merge_required = str(needs_merging).lower() == "true"
    return {
        "needs_merging_raw": needs_merging,
        "needs_merging_type": str(type(needs_merging)),
        "is_merge_required": is_merge_required,
        "original_url_present": bool(original_url),
        "would_take_path": "merge" if (is_merge_required and original_url) else "proxy"
    }

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
    import tempfile
    import os
    from fastapi.responses import StreamingResponse, FileResponse

    # CASE 1: High Quality Merging (Needs FFmpeg)
    is_merge_required = str(needs_merging).lower() == "true"
    
    if is_merge_required and original_url:
        try:
            logger.info(f"Starting temp-file merged download for: {original_url}")
            
            # Create a temp directory that persists until we stream the file
            tmp_dir = tempfile.mkdtemp()
            output_path = os.path.join(tmp_dir, "output.mp4")

            # yt-dlp downloads DASH segments + merges with FFmpeg into a real MP4 file
            # Piping DASH to stdout doesn't work — segments must be assembled on disk first
            cmd = [
                "yt-dlp",
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--no-playlist",
                "-o", output_path,
                original_url
            ]
            
            if downloader_service.ydl_opts.get('cookiefile'):
                cmd.extend(["--cookies", downloader_service.ydl_opts['cookiefile']])

            logger.info(f"Running yt-dlp merge command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 min max
            )

            if result.returncode != 0:
                logger.error(f"yt-dlp merge failed: {result.stderr}")
                raise Exception(f"yt-dlp failed: {result.stderr[:200]}")

            if not os.path.exists(output_path):
                raise Exception("Output file not created by yt-dlp")

            logger.info(f"Merge successful, streaming file: {output_path}")

            encoded_title = urllib.parse.quote(title)

            def stream_and_cleanup():
                try:
                    with open(output_path, "rb") as f:
                        while True:
                            chunk = f.read(1024 * 64)
                            if not chunk:
                                break
                            yield chunk
                finally:
                    # Clean up temp files after streaming
                    try:
                        os.remove(output_path)
                        os.rmdir(tmp_dir)
                    except Exception:
                        pass

            headers = {
                'Content-Disposition': f"attachment; filename*=utf-8''{encoded_title}.mp4",
                'Content-Length': str(os.path.getsize(output_path)),
                'X-Path-Taken': 'merge'
            }
            return StreamingResponse(stream_and_cleanup(), media_type="video/mp4", headers=headers)

        except Exception as e:
            logger.error(f"Smart merge failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Merge failed: {str(e)}"
            )

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
        headers = {
            'Content-Disposition': f"attachment; filename*=utf-8''{encoded_title}.{ext}",
            'X-Path-Taken': 'proxy'
        }
        return StreamingResponse(iterfile(), media_type="application/octet-stream", headers=headers)
    except Exception as e:
        logger.error(f"Error proxying download: {e}")
        raise HTTPException(status_code=400, detail=str(e))
