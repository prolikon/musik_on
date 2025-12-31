import os

import yt_dlp


def get_playlist_info(playlist_url):
    ydl_opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:  # pyright: ignore[reportArgumentType]
        return ydl.extract_info(playlist_url, download=False)

        # return info


def audio_exists(filename):
    file_path = os.path.join("app", "static", "media", f"{filename}.mp3")
    return os.path.exists(file_path)


def video_exists(filename):
    file_path = os.path.join("app", "static", "media", f"{filename}.mp4")
    return os.path.exists(file_path)
