import sys
import json
import time
import requests
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright

import os

def download_file(url, filename):
    print(f"Downloading {url}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    # Ensure downloads directory exists
    os.makedirs('downloads', exist_ok=True)
    filepath = os.path.join('downloads', filename)
    
    with open(filepath, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    # Safely print filename to avoid UnicodeEncodeError on Windows console
    safe_filename = filename.encode(sys.stdout.encoding, errors='replace').decode(sys.stdout.encoding)
    print(f"Saved to {safe_filename}")
    return filepath

def scrape_starmaker(url):
    media_url = None
    title = None
    
    print("Starting browser...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Emulate a mobile device to ensure mobile API is called
        iphone_13 = p.devices['iPhone 13']
        context = browser.new_context(**iphone_13)
        page = context.new_page()
        
        def handle_response(response):
            nonlocal media_url, title
            try:
                if "new_detail" in response.url and "application/json" in response.headers.get("content-type", ""):
                    data = response.json()
                    if "sm" in data and "record" in data["sm"]:
                        recording = data["sm"]["record"].get("recording", {})
                        song = data["sm"]["record"].get("song", {})
                        user = data["sm"]["record"].get("user", {})
                        
                        media_url = recording.get("mp4_media_url") or recording.get("media_url")
                        
                        song_title = song.get("title", "Unknown Song")
                        artist = song.get("artist", "Unknown Artist")
                        username = user.get("name", "Unknown User")
                        
                        # Clean up title for filename by removing invalid Windows characters
                        raw_title = f"{username} - {song_title} ({artist})"
                        import re
                        title = re.sub(r'[<>:"/\\|?*]', '_', raw_title)
            except Exception:
                pass
                
        page.on("response", handle_response)
        
        print(f"Navigating to {url}...")
        try:
            page.goto(url, wait_until="networkidle", timeout=15000)
        except Exception as e:
            print("Navigation finished or timed out. Checking if we intercepted the URL...")
            
        time.sleep(2) # Allow any pending JS to process
        browser.close()
        
    if media_url:
        print(f"Found media URL: {media_url}")
        
        ext = ".mp4" if ".mp4" in media_url else ".m4a"
        filename = f"{title}{ext}" if title else f"starmaker_download{ext}"
        
        filepath = download_file(media_url, filename)
        return {"success": True, "filepath": filepath, "filename": filename}
    else:
        print("Could not find the media URL. The page structure might have changed or the link is invalid.")
        return {"success": False, "error": "Could not find media URL"}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python starmaker_scraper.py <starmaker_url>")
        sys.exit(1)
        
    target_url = sys.argv[1]
    scrape_starmaker(target_url)
