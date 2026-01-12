import asyncio
from os import getenv, path
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from socketio import ASGIApp, AsyncServer
from starlette.middleware.sessions import SessionMiddleware

load_dotenv()

from . import db  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=getenv("secret_key"))
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")

templates = Jinja2Templates(BASE_DIR / "template")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")


def render(template_name, request, **kwargs):
    return templates.TemplateResponse(template_name, {"request": request, **kwargs})


# Initialise the required queues
from .task import TaskQueue, worker_loop, ytdl, ytmusic  # noqa: E402

audio_queue = TaskQueue(ytdl.download_audio)
video_queue = TaskQueue(ytdl.download_video)
yt_search_queue = TaskQueue(ytmusic.find_youtube_tracksource)

if not path.exists("app.db"):
    from .db import models  # noqa: F401

    # Import models to add them to the Base before initialising the database!!
    asyncio.create_task(db.init_db())

# Attach the routes and shit
from . import route, websocket  # noqa: F401 E402

asyncio.create_task(worker_loop(audio_queue, video_queue))
asyncio.create_task(worker_loop(video_queue, audio_queue))
asyncio.create_task(worker_loop(yt_search_queue))

sio_app = ASGIApp(sio, other_asgi_app=app)
