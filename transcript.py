from youtube_transcript_api import YouTubeTranscriptApi
import re
import urllib.request
import json
import os
import requests

# ─────────────────────────────────────────
# 1. URL VALIDATOR & VIDEO ID EXTRACTOR
# ─────────────────────────────────────────

def extract_video_id(url: str):
    url = url.strip()

    if "list=" in url and "watch?v=" not in url:
        return None, "❌ This looks like a playlist link. Please paste a single video URL."

    patterns = [
        r"(?:v=)([a-zA-Z0-9_-]{11})",
        r"(?:youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), None

    return None, "❌ Invalid YouTube URL. Please check the link and try again."


# ─────────────────────────────────────────
# 2. TRANSCRIPT FETCHER (updated API)
# ─────────────────────────────────────────

def fetch_transcript(url: str):
    video_id, url_error = extract_video_id(url)
    if url_error:
        return {"error": url_error}

    try:
        # Get ScraperAPI key — from Streamlit secrets (cloud) or .env (local)
        scraper_key = None
        try:
            import streamlit as st
            scraper_key = st.secrets.get("SCRAPERAPI_KEY")
        except Exception:
            scraper_key = os.getenv("SCRAPERAPI_KEY")

        # Use proxy on cloud, direct on local
        if scraper_key:
            proxies = {
                "http": f"http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001",
                "https": f"http://scraperapi:{scraper_key}@proxy-server.scraperapi.com:8001",
            }
            session = requests.Session()
            session.proxies.update(proxies)
            session.verify = False
            yt = YouTubeTranscriptApi(http_client=session)
        else:
            yt = YouTubeTranscriptApi()

        transcript_list = yt.list(video_id)

        transcript = None
        is_auto_generated = False
        language_code = "en"
        language_name = "English"

        # Priority 1: Manual English transcript
        try:
            transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB'])
            language_code = transcript.language_code
            language_name = transcript.language
            is_auto_generated = False

        except Exception:
            # Priority 2: Any manual transcript
            try:
                all_codes = [t.language_code for t in transcript_list]
                transcript = transcript_list.find_manually_created_transcript(all_codes)
                language_code = transcript.language_code
                language_name = transcript.language
                is_auto_generated = False

            except Exception:
                # Priority 3: Any auto-generated transcript
                try:
                    all_codes = [t.language_code for t in transcript_list]
                    transcript = transcript_list.find_generated_transcript(all_codes)
                    language_code = transcript.language_code
                    language_name = transcript.language
                    is_auto_generated = True

                except Exception:
                    return {"error": "❌ No transcript found. The creator may have disabled captions."}

        # Fetch actual transcript data
        transcript_data = transcript.fetch()

        # Build full text — handle both old and new API response format
        full_text = " ".join([
            entry.get('text', '') if isinstance(entry, dict) else getattr(entry, 'text', '')
            for entry in transcript_data
        ])
        full_text = clean_transcript(full_text)

        # Duration
        try:
            last = transcript_data[-1]
            if isinstance(last, dict):
                duration_seconds = last.get('start', 0) + last.get('duration', 0)
            else:
                duration_seconds = getattr(last, 'start', 0) + getattr(last, 'duration', 0)
            duration_minutes = round(duration_seconds / 60, 1)
        except Exception:
            duration_minutes = 0

        # Warnings
        warning = None
        if len(full_text.split()) < 50:
            warning = "⚠️ Very little spoken content found. Summary may be limited."
        if is_auto_generated:
            warning = (warning or "") + "\n⚠️ Using auto-generated captions — accuracy may vary."

        is_english = language_code.startswith('en')
        chunks = chunk_transcript(full_text)

        return {
            "text": full_text,
            "language": language_code,
            "language_name": language_name,
            "is_english": is_english,
            "is_auto_generated": is_auto_generated,
            "warning": warning,
            "chunks": chunks,
            "duration_minutes": duration_minutes,
            "video_id": video_id
        }

    except Exception as e:
        error_str = str(e).lower()
        if "private" in error_str:
            return {"error": "❌ This video is private."}
        elif "not found" in error_str or "404" in error_str:
            return {"error": "❌ Video not found. Please check the URL."}
        elif "disabled" in error_str:
            return {"error": "❌ Transcripts are disabled for this video."}
        elif "unavailable" in error_str:
            return {"error": "❌ This video is unavailable."}
        elif "ip" in error_str or "blocked" in error_str or "could not retrieve" in error_str:
            return {"error": (
                "⚠️ YouTube is blocking transcript access from this server's IP — "
                "this is a known limitation when running on cloud platforms like Streamlit Cloud. "
                "The app works perfectly when run locally. "
                "Please refer to the demo video to see it in action, "
                "or clone the repo and run: streamlit run app.py"
            )}
        else:
            return {"error": f"❌ Something went wrong: {str(e)}"}


# ─────────────────────────────────────────
# 3. CLEANER
# ─────────────────────────────────────────

def clean_transcript(text: str) -> str:
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


# ─────────────────────────────────────────
# 4. CHUNKER
# ─────────────────────────────────────────

def chunk_transcript(text: str, max_words: int = 3000) -> list:
    words = text.split()
    if len(words) <= max_words:
        return [text]

    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        chunks.append(chunk)
    return chunks


# ─────────────────────────────────────────
# 5. VIDEO TITLE FETCHER
# ─────────────────────────────────────────

def fetch_video_title(video_id: str) -> str:
    """
    Fetches the actual YouTube video title using YouTube's oEmbed API.
    No API key required — completely free.
    """
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        with urllib.request.urlopen(url, timeout=5) as response:
            data = json.loads(response.read().decode())
            return data.get("title", "")
    except Exception:
        return ""
