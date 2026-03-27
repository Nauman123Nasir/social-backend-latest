from app.services.downloader import downloader_service
import json

try:
    url = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo (first youtube video)
    info = downloader_service.get_video_info(url)
    print(json.dumps(info, indent=2))
except Exception as e:
    print(f"Error: {e}")
