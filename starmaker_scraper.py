import os
import re
import sys
import time
from urllib.parse import unquote, urlparse

import requests
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


MEDIA_EXTENSIONS = (
    ".m4a",
    ".mp3",
    ".mp4",
    ".m3u8",
    ".aac",
    ".wav",
)

REJECTED_MEDIA_PATTERNS = (
    "/cover_image",
    "/template_res/",
    "template_",
    "score_resource",
    "/stchat/audio/",
    "profile.jpg",
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
    ".zip",
    ".json",
    ".txt",
    "/a-vue3/playrecording",
)

MEDIA_CONTENT_TYPES = (
    "audio/",
    "video/",
    "application/octet-stream",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
)

MEDIA_URL_HINTS = (
    "media",
    "audio",
    "video",
    "recording",
    "sing",
    "m4a",
    "mp3",
    "mp4",
    "m3u8",
)


def sanitize_filename(value):
    cleaned = re.sub(r'[<>:"/\\|?*]', "_", value or "starmaker_download")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ._")
    return cleaned[:160] or "starmaker_download"


def looks_like_media_url(value, allow_hints=False):
    if not isinstance(value, str) or not value.startswith(("http://", "https://")):
        return False

    lower_value = unquote(value).lower()
    parsed_path = urlparse(lower_value).path

    if any(pattern in lower_value for pattern in REJECTED_MEDIA_PATTERNS):
        return False

    return (
        any(ext in parsed_path for ext in MEDIA_EXTENSIONS)
        or (allow_hints and any(hint in lower_value for hint in MEDIA_URL_HINTS))
    )


def find_media_urls(value):
    urls = []

    if isinstance(value, dict):
        for key, child in value.items():
            lower_key = str(key).lower()
            if isinstance(child, str) and child.startswith(("http://", "https://")):
                if looks_like_media_url(child, allow_hints=True) or any(hint in lower_key for hint in MEDIA_URL_HINTS):
                    urls.append(child)
            urls.extend(find_media_urls(child))
    elif isinstance(value, list):
        for child in value:
            urls.extend(find_media_urls(child))
    elif looks_like_media_url(value, allow_hints=True):
        urls.append(value)

    return urls


def first_text(value, keys):
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key).lower() in keys and isinstance(child, str) and child.strip():
                return child.strip()

        for child in value.values():
            found = first_text(child, keys)
            if found:
                return found
    elif isinstance(value, list):
        for child in value:
            found = first_text(child, keys)
            if found:
                return found

    return None


def choose_media_url(candidates):
    unique_candidates = []
    seen = set()

    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        unique_candidates.append(candidate)

    if not unique_candidates:
        return None

    priority = (".m4a", ".mp3", ".mp4", ".m3u8")
    for ext in priority:
        for candidate in unique_candidates:
            if ext in unquote(candidate).lower():
                return candidate

    return unique_candidates[0]


def extension_for_url(url):
    lower_path = unquote(urlparse(url).path).lower()
    for ext in (".mp4", ".m4a", ".mp3", ".aac", ".wav"):
        if ext in lower_path:
            return ext
    return ".mp4" if "video" in lower_path else ".m4a"


def is_downloadable_recording_url(url):
    lower_value = unquote(url).lower()
    lower_path = urlparse(lower_value).path

    return (
        "/production/uploading/recordings/" in lower_value
        and any(ext in lower_path for ext in (".mp4", ".m4a", ".mp3", ".aac", ".wav"))
        and not any(pattern in lower_value for pattern in REJECTED_MEDIA_PATTERNS)
    )


def download_file(url, filename):
    print(f"Downloading {url}...", flush=True)
    response = requests.get(
        url,
        stream=True,
        timeout=60,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
            ),
            "Referer": "https://m.starmakerstudios.com/",
        },
    )
    response.raise_for_status()

    os.makedirs("downloads", exist_ok=True)
    filepath = os.path.join("downloads", filename)

    with open(filepath, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)

    safe_filename = filename.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
    print(f"Saved to {safe_filename}", flush=True)
    return filepath


def click_if_present(page, selector, label):
    try:
        locator = page.locator(selector).first
        if locator.count() and locator.is_visible(timeout=1000):
            print(f"Clicking {label}...", flush=True)
            locator.click(timeout=3000)
            page.wait_for_timeout(1500)
            return True
    except Exception:
        pass
    return False


def log_visible_buttons(page):
    try:
        labels = page.locator("button, [role='button'], a").evaluate_all(
            """
            elements => elements
                .map(element => (element.innerText || element.textContent || element.getAttribute('aria-label') || '').trim())
                .filter(Boolean)
                .slice(0, 12)
            """
        )
        if labels:
            print(f"Visible actions: {labels}", flush=True)
    except Exception:
        pass


def click_first_available(page, selectors, label):
    for selector in selectors:
        if click_if_present(page, selector, label):
            return True
    return False


def trigger_playback(page):
    log_visible_buttons(page)

    play_selectors = [
        "button:has-text('Play')",
        "text=/^Play$/i",
        "[aria-label*='play' i]",
        ".play",
        ".play-btn",
        ".player-play",
    ]
    if click_first_available(page, play_selectors, "play control"):
        page.wait_for_timeout(2200)
        log_visible_buttons(page)

    popup_selectors = [
        "button:has-text('Go')",
        "text=/^Go$/i",
        "button:has-text('Cancel')",
        "text=/^Cancel$/i",
        "button:has-text('OK')",
        "text=/^OK$/i",
        "button:has-text('Continue')",
        "text=/^Continue$/i",
        "button:has-text('Not now')",
        "text=/^Not now$/i",
        "button:has-text('Open StarMaker')",
        "text=/Open StarMaker/i",
    ]
    if click_first_available(page, popup_selectors, "StarMaker popup action"):
        page.wait_for_timeout(2500)
        return

    print("No visible playback controls matched; trying fallback tap.", flush=True)
    try:
        page.mouse.click(190, 360)
        page.wait_for_timeout(2500)
    except Exception:
        pass


def scrape_starmaker(url):
    media_candidates = []
    capture_state = {"enabled": False}
    title = None

    print("Starting browser...", flush=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        iphone_13 = playwright.devices["iPhone 13"]
        context = browser.new_context(**iphone_13)
        page = context.new_page()

        def remember_media(candidate, source):
            if not capture_state["enabled"]:
                print(f"Ignoring pre-playback media candidate from {source}: {candidate}", flush=True)
                return
            if not is_downloadable_recording_url(candidate):
                print(f"Ignoring non-recording media candidate from {source}: {candidate}", flush=True)
                return
            if candidate and candidate not in media_candidates:
                print(f"Captured possible media URL from {source}: {candidate}", flush=True)
                media_candidates.append(candidate)

        def handle_request(request):
            request_url = request.url
            if looks_like_media_url(request_url):
                remember_media(request_url, "request")

        def handle_response(response):
            nonlocal title

            response_url = response.url
            content_type = response.headers.get("content-type", "").lower()

            if any(content_type.startswith(prefix) for prefix in MEDIA_CONTENT_TYPES):
                remember_media(response_url, f"response content-type {content_type}")

            if looks_like_media_url(response_url):
                remember_media(response_url, "response url")

            if "json" not in content_type and "new_detail" not in response_url:
                return

            try:
                data = response.json()
            except Exception:
                return

            if capture_state["enabled"]:
                for candidate in find_media_urls(data):
                    remember_media(candidate, "json")

            if not title:
                username = first_text(data, {"username", "user_name", "name", "nickname"})
                song_title = first_text(data, {"title", "song_title", "songname", "song_name"})
                artist = first_text(data, {"artist", "artist_name", "singer"})

                title_parts = [part for part in (username, song_title, artist) if part]
                if title_parts:
                    title = sanitize_filename(" - ".join(title_parts[:3]))

        page.on("request", handle_request)
        page.on("response", handle_response)

        print(f"Navigating to {url}...", flush=True)
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except PlaywrightTimeoutError:
            print("Initial navigation timed out; continuing with loaded page state.", flush=True)

        for attempt in range(3):
            page.wait_for_timeout(1000)
            if media_candidates:
                break
            if not capture_state["enabled"]:
                print("Starting post-playback media capture window.", flush=True)
                media_candidates.clear()
                capture_state["enabled"] = True
            trigger_playback(page)
            if media_candidates:
                break
            page.wait_for_timeout(1500)
            if media_candidates:
                break

        if not title:
            try:
                page_title = page.title()
                title = sanitize_filename(page_title)
            except Exception:
                title = None

        browser.close()

    media_url = choose_media_url(media_candidates)

    if media_url:
        print(f"Found media URL: {media_url}", flush=True)
        ext = extension_for_url(media_url)
        filename = f"{title}{ext}" if title else f"starmaker_download{ext}"

        filepath = download_file(media_url, filename)
        return {"success": True, "filepath": filepath, "filename": filename}

    print("Could not find the media URL. The page may require the StarMaker app or a changed playback flow.", flush=True)
    return {"success": False, "error": "Could not find media URL after loading and attempting playback"}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python starmaker_scraper.py <starmaker_url>")
        sys.exit(1)

    target_url = sys.argv[1]
    scrape_starmaker(target_url)
