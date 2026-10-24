import os
import asyncio
import aiohttp
from youtube_search import YoutubeSearch
import yt_dlp

from clients import LOGGER

NEXOR_STREAM_URL = os.environ.get("NEXOR_STREAM_URL", "https://nexor-yt-pannl.lovable.app")
NEXOR_STREAM_KEY = os.environ.get("NEXOR_STREAM_KEY", "NEXOR_3481fsghsh62ghs")

DOWNLOADS_DIR = os.path.join(os.getcwd(), "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

YTDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "extract_flat": False,
    "nocheckcertificate": True,
    "geo_bypass": True,
}


class DownloadError(Exception):
    """API se gaana ready nahi ho paya."""


def _video_id(video: str) -> str:
    video = (video or "").strip()
    if not video:
        return ""
    if "youtu.be/" in video:
        video = video.split("youtu.be/")[1]
    elif "v=" in video:
        video = video.split("v=")[1]
    elif "/shorts/" in video:
        video = video.split("/shorts/")[1]
    elif "/embed/" in video:
        video = video.split("/embed/")[1]
    for sep in ("?", "&", "/", "#"):
        video = video.split(sep)[0]
    return video


async def search_youtube(query: str):
    loop = asyncio.get_event_loop()

    def _search():
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            return results[0] if results else None
        except Exception as e:
            LOGGER.warning(f"YouTube search error: {e}")
            return None

    return await loop.run_in_executor(None, _search)


async def search_track(query: str):
    result = await search_youtube(query)
    if not result:
        return None

    thumbnails = result.get("thumbnails") or []
    video_id = result.get("id")

    return {
        "id": video_id,
        "title": result.get("title", "Unknown"),
        "duration": result.get("duration", "03:45"),
        "thumbnail": thumbnails[0] if thumbnails else None,
        "channel": result.get("channel") or result.get("uploader") or "YouTube Music",
        "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
    }


def _download_song_local(video_id: str) -> str:
    target_file = os.path.join(DOWNLOADS_DIR, f"{video_id}.mp3")
    if os.path.exists(target_file) and os.path.getsize(target_file) > 1024:
        return target_file

    url = f"https://www.youtube.com/watch?v={video_id}"
    opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(DOWNLOADS_DIR, f"{video_id}.%(ext)s"),
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
    }
    with yt_dlp.YoutubeDL(opts) as ytdl:
        ytdl.download([url])

    if os.path.exists(target_file):
        return target_file

    # Fallback to direct url extraction
    with yt_dlp.YoutubeDL(YTDL_OPTS) as ytdl:
        info = ytdl.extract_info(url, download=False)
        return info.get("url")


async def get_stream_url(video: str) -> str:
    video_id = _video_id(video)
    if not video_id:
        raise DownloadError("Video ID not found.")

    # 1. Try Nexor API (3 second timeout)
    if NEXOR_STREAM_URL:
        stream_url = f"{NEXOR_STREAM_URL}/stream/{video_id}?key={NEXOR_STREAM_KEY}"
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(stream_url) as resp:
                    if resp.status == 200:
                        return stream_url
        except Exception:
            LOGGER.info("Nexor API unavailable, switching to local audio engine.")

    # 2. Local Fast Extraction via yt-dlp
    loop = asyncio.get_event_loop()
    try:
        audio_source = await loop.run_in_executor(None, _download_song_local, video_id)
        if audio_source:
            return audio_source
    except Exception as e:
        LOGGER.error(f"Audio extraction failed: {e}")
        raise DownloadError(f"Audio engine error: {e}")

    raise DownloadError("Unable to fetch audio stream.")