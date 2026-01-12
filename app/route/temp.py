import re

from fastapi import Form, Request
from fastapi.responses import RedirectResponse

from .. import app, render
from ..util import youtube

yt_pattern = r'(?:youtube\.com\/(?:[^\/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?\/\s]{11})'


# Home page
@app.get("/")
def index(request: Request):
    return render("page/index.html", request)


@app.post("/api/route")
def api_route(url: str = Form("")):
    match = re.search(yt_pattern, url)
    if match:
        video_id = match.group(1)
        return RedirectResponse(url=f"/yt/{video_id}", status_code=302)

    return RedirectResponse(url="/", status_code=302)


@app.get("/yt/{video_id}")
def video(request: Request, video_id: str):
    audio_status = -2
    if youtube.audio_exists(video_id):
        audio_status = -1

    video_status = -2
    if youtube.video_exists(video_id):
        video_status = -1

    return render(
        "page/video.html",
        request,
        video_id=video_id,
        audio_status=audio_status,
        video_status=video_status,
    )


@app.get("/pl/{pl_id}")
def playlist(request: Request, pl_id: str):
    info = youtube.get_playlist_info(pl_id)
    entries = []

    for entry in info["entries"]:  # pyright: ignore[reportGeneralTypeIssues]
        audio_status = -2
        if youtube.audio_exists(entry["id"]):
            audio_status = -1

        entries.append(
            {
                "id": entry["id"],
                "status": audio_status,
                "title": entry["title"],
                "artist": entry["uploader"],
            }
        )

    return render("page/playlist.html", request, videos=entries)
