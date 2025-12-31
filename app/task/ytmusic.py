from ytmusicapi import YTMusic

from .. import sio
from ..db import AsyncSessionLocal
from ..db.models import TrackMeta, TrackSource

ytmusic = YTMusic()


async def find_youtube_tracksource(meta: TrackMeta):
    result = ytmusic.search(
        query=f"{meta.artist} - {meta.title}",
        filter="songs",
        limit=1,
        ignore_spelling=True,
    )[0]  # We only want the first result :)

    video_id = result.get("videoId", "WTF?")

    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        # create new youtube Source and link to Meta
        spotify_source = TrackSource(
            source="youtube",
            id=video_id,
            track_meta=meta,
        )
        session.add(spotify_source)
        await session.commit()

    await sio.emit("task_complete", {"task": "youtube_source", "video_id": video_id})
