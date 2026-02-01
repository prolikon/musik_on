from os import getenv

import spotipy
from fastapi import Request
from spotipy.oauth2 import SpotifyClientCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import app, render, yt_search_queue
from ..db import AsyncSessionLocal
from ..db.models import TrackMeta, TrackSource
from ..util.spotify import get_spotify_playlist
from ..util.youtube import audio_exists

Spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=getenv("spotify_client_id"),
        client_secret=getenv("spotify_client_secret"),
    )
)


# this route should be called by the client when they load the /spotify/plid/load page.
# it finds which songs don't have a TrackSource to download from (youtube, local),
# sends their IDs to the client, and queues youtube sourcing tasks.
@app.get("/spotify/{pl_id}/load")
async def spotify_playlist_load(pl_id: str):
    # get spotify playlist
    tracks = (await get_spotify_playlist(pl_id, no_update=True))["tracks"]
    resp = []

    spotify_ids = [track["id"] for track in tracks]

    # spotify tracksource -> trackmeta -> youtube tracksource
    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        spotify_sources_result = await session.execute(
            select(TrackSource)
            .where(TrackSource.source == "spotify", TrackSource.id.in_(spotify_ids))
            .options(  # No lazy loading with async!!
                selectinload(TrackSource.track_meta).selectinload(TrackMeta.sources)
            )
        )
        spotify_sources = spotify_sources_result.scalars().all()

        spotify_source_by_id = {source.id: source for source in spotify_sources}
        missing_metas = []
        meta_mapping = {}

        for track in tracks:
            spotify_id = track["id"]
            if spotify_id not in spotify_source_by_id:
                missing_metas.append((track["artists"][0], track["title"]))
                meta_mapping[spotify_id] = (track["artists"][0], track["title"])

        metas_by_key = await TrackMeta.batch_get_or_create(session, missing_metas)

        new_sources = []
        for spotify_id, (artist, title) in meta_mapping.items():
            meta = metas_by_key[(artist, title)]
            new_source = TrackSource(source="spotify", id=spotify_id, track_meta=meta)

            new_sources.append(new_source)
            meta.sources.append(new_source)

        if new_sources:
            session.add_all(new_sources)
            await session.commit()

    missing = []
    for track in tracks:
        meta = metas_by_key[(track["artists"][0], track["title"])]

        local = next((s for s in meta.sources if s.source == "local"), None)
        youtube = next((s for s in meta.sources if s.source == "youtube"), None)

        source = local or youtube

        if not source:
            resp.append(
                {"spotify_id": track["id"], "meta_id": meta.id, "missing": True}
            )
            missing.append(meta)
        else:
            resp.append(
                {"spotify_id": track["id"], "meta_id": meta.id, "missing": False}
            )

    for meta in missing:
        await yt_search_queue.put(meta)

    return resp


def _loading_page(request: Request, tracks, playlist_meta):
    entries = []

    for entry in tracks:  # pyright: ignore[reportGeneralTypeIssues]
        entries.append(
            {
                "id": entry["id"],
                "title": entry["title"],
                "artist": entry["artists"][0],
                "image": entry["image"][1]["url"],
            }
        )

    return render(
        "page/spotify_playlist_load.html",
        request,
        tracks=tracks,
        playlist=playlist_meta,
    )


@app.get("/spotify/{pl_id}")
async def spotify_playlist(request: Request, pl_id: str):
    playlist = await get_spotify_playlist(pl_id)
    playlist_meta = {
        "thumbnail": playlist["thumbnail"],
        "name": playlist["name"],
        "description": playlist["description"],
        "id": pl_id,
    }
    tracks_sp = playlist["tracks"]
    tracks_yt = []

    spotify_ids = [track["id"] for track in tracks_sp]

    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        spotify_sources_result = await session.execute(
            select(TrackSource)
            .where(TrackSource.source == "spotify", TrackSource.id.in_(spotify_ids))
            .options(  # No lazy loading with async!!
                selectinload(TrackSource.track_meta).selectinload(TrackMeta.sources)
            )
        )
        spotify_sources = spotify_sources_result.scalars().all()

    if len(spotify_sources) != len(spotify_ids):
        return _loading_page(request, tracks_sp, playlist_meta)

    for source in spotify_sources:
        meta = source.track_meta

        # local = next((s for s in meta.sources if s.source == "local"), None)
        youtube = next((s for s in meta.sources if s.source == "youtube"), None)

        if youtube:
            tracks_yt.append(
                {
                    "id": youtube.id,
                    "title": meta.title,
                    "artist": meta.artist,
                }
            )
        else:
            return _loading_page(request, tracks_sp, playlist_meta)

    for track in tracks_yt:
        audio_status = -2
        if audio_exists(track["id"]):
            audio_status = -1

        track["status"] = audio_status

    return render(
        "page/playlist.html", request, videos=tracks_yt, playlist=playlist_meta
    )
