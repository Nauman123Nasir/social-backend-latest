from app.services.downloader import downloader_service
import json

try:
    url = "https://x.com/Pokemon/status/1769363063533285775" # sample twitter video
    info = downloader_service.get_video_info(url)
    print(json.dumps(info, indent=2))
except Exception as e:
    print(f"Error: {e}")
