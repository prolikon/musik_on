import asyncio

import yt_dlp

from .. import sio

audio_opts = {
    # "quiet": True,
    #'no_color': True,
    #'no_warnings': True,
    "format": "bestaudio/best",
    "outtmpl": "app/static/media/%(id)s.%(ext)s",
    "writethumbnail": True,
    "embedthumbnail": True,
    "postprocessors": [
        {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
        {"key": "FFmpegMetadata"},
        {"key": "EmbedThumbnail"},
    ],
    "keepvideo": False,
}


async def download_audio(video_id):
    await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(audio_opts).download([video_id]))  # pyright: ignore[reportArgumentType]
    await sio.emit("task_complete", {"task": "request_audio", "video_id": video_id})


video_opts = {
    # "quiet": True,
    "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]",
    "outtmpl": "app/static/media/%(id)s.%(ext)s",  # Using video ID only
    "merge_output_format": "mp4",
    "writethumbnail": True,
    "embedthumbnail": True,
    "postprocessors": [
        {"key": "FFmpegMetadata"},
        {"key": "EmbedThumbnail"},
    ],
}


async def download_video(video_id):
    # with yt_dlp.YoutubeDL(video_opts) as ydl:  # pyright: ignore[reportArgumentType]
    #    ydl.download(video_id)

    await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(video_opts).download([video_id]))  # pyright: ignore[reportArgumentType]

    await sio.emit("task_complete", {"task": "request_video", "video_id": video_id})
