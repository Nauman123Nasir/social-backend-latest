import yt_dlp
import sys
import json

ydl_opts = {
    'quiet': True,
    'no_warnings': True,
}

def debug_formats(url):
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            print(f"Extractor: {info.get('extractor')}")
            print(f"Title: {info.get('title')}")
            print("-" * 40)
            print(f"{'Format ID':<15} {'Ext':<5} {'Res':<10} {'Vcodec':<10} {'Acodec':<10} {'Size':<10}")
            for f in info.get('formats', []):
                vcodec = f.get('vcodec', 'none')
                acodec = f.get('acodec', 'none')
                height = f.get('height', 'n/a')
                ext = f.get('ext', 'n/a')
                fid = f.get('format_id', 'n/a')
                size = f.get('filesize', 0) or 0
                size_mb = f"{size / (1024*1024):.2f}MB" if size else "unknown"
                
                print(f"{fid:<15} {ext:<5} {height:<10} {vcodec:<10} {acodec:<10} {size_mb:<10}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_formats(sys.argv[1])
    else:
        print("Usage: python debug_yt.py <url>")
