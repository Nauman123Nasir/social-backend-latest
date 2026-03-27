import yt_dlp
from typing import Dict, Any
import os

class VideoDownloader:
    def __init__(self):
        # Base options for yt-dlp to extract info quickly without downloading
        self.ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'getcomments': False,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'en-US,en;q=0.9',
                'Sec-Ch-Ua': '"Chromium";v="122", "Not(A:Brand";v="24", "Google Chrome";v="122"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
            },
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }
        
        # Check for cookies in Environment Variable first (Ideal for Vercel/Servers)
        env_cookies = os.environ.get("YTDLP_COOKIES")
        if env_cookies:
            import tempfile
            # Create a temporary file and write the cookies to it
            fd, temp_path = tempfile.mkstemp(suffix=".txt", text=True)
            with os.fdopen(fd, 'w') as f:
                # Replace escaped newlines with actual newlines if user pasted a single line string
                f.write(env_cookies.replace('\\n', '\n'))
            self.ydl_opts['cookiefile'] = temp_path
        else:
            # Fallback to local cookies.txt file
            cookies_path = os.path.join(os.getcwd(), 'cookies.txt')
            if os.path.exists(cookies_path):
                self.ydl_opts['cookiefile'] = cookies_path

    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extracts video metadata and direct download URLs using yt-dlp
        """
        if "tiktok.com" in url.lower():
            raise Exception("TikTok is not supported.")
        if "youtube.com" in url.lower() or "youtu.be" in url.lower():
            raise Exception("YouTube downloads are temporarily disabled.")
            
        # Strategy: Try to extract info with current ydl_opts.
        # If it fails due to auth/cookies, we might try to report that specifically.
        try:
            with yt_dlp.YoutubeDL(self.ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return self._parse_info(info, url)
        except Exception as e:
            error_msg = str(e)
            if "Instagram sent an empty media response" in error_msg or "login" in error_msg.lower():
                 raise Exception("Instagram/Facebook requires authentication.")
            if "Sign in to confirm" in error_msg:
                 raise Exception("YouTube blocked the request. Please try again later.")
                
            raise Exception(f"Failed to extract video info: {error_msg}")

    def _parse_info(self, info: Dict[str, Any], url: str) -> Dict[str, Any]:
        # Filter formats to only include those with video (and preferably audio)
        # Sort by resolution/quality
        formats = []
        
        # determine platform from extractor key
        extractor = info.get('extractor_key', 'Unknown').lower()
        platform = extractor if extractor else 'Unknown'
        
        if 'formats' in info:
            for f in info['formats']:
                # Filter out audio-only or formats without a direct URL
                if f.get('vcodec') != 'none' and f.get('ext') in ['mp4', 'webm'] and f.get('url'):
                    # Simplify resolution string
                    height = f.get('height')
                    resolution = f"{height}p" if height else f.get('format_note', 'unknown')
                    
                    formats.append({
                        'format_id': f.get('format_id', ''),
                        'ext': f.get('ext', ''),
                        'resolution': resolution,
                        'filesize': f.get('filesize'),
                        'url': f.get('url', '')
                    })
        else:
            # Fallback for platforms that might just return a single direct URL
            formats.append({
                'format_id': 'default',
                'ext': info.get('ext', 'mp4'),
                'resolution': 'default',
                'url': info.get('url', '')
            })

        # Remove duplicates based on resolution and ext
        unique_formats = []
        seen = set()
        for f in formats:
            key = f"{f['resolution']}_{f['ext']}"
            if key not in seen:
                seen.add(key)
                unique_formats.append(f)

        return {
            'title': info.get('title', 'Unknown Title'),
            'thumbnail': info.get('thumbnail'),
            'duration': info.get('duration'),
            'formats': unique_formats,
            'platform': platform
        }

downloader_service = VideoDownloader()
