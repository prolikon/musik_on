from os import getenv

import spotipy
from fastapi import Request
from spotipy.oauth2 import SpotifyClientCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .. import app, render, yt_search_queue
from ..db import AsyncSessionLocal
from ..db.models import TrackMeta, TrackSource
from ..util.youtube import audio_exists

Spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=getenv("spotify_client_id"),
        client_secret=getenv("spotify_client_secret"),
    )
)


def get_spotify_playlist(playlist_id):
    result = Spotify.playlist(
        playlist_id,
        fields="images,name,description,tracks(next,items(track(id,name,artists(name),album(images))))",
    )
    tracks = result.get("tracks")
    songs = []

    # Results can contain multiple pages, we dunno how many so we have to use a while loop.
    while tracks:
        for item in tracks["items"]:
            track = item["track"]
            if track:  # Check if track exists for item
                song_info = {
                    "id": item["track"]["id"],
                    "title": track["name"],
                    "artists": [artist["name"] for artist in track["artists"]],
                    "image": track["album"]["images"],
                }
                songs.append(song_info)

        # Check if there are more pages
        if tracks["next"]:
            tracks = Spotify.next(tracks)
        else:
            break

    description = result["description"]
    if description == "":
        description = (
            "this spotify playlist has no description. that's pretty lame dawg."
        )

    return {
        "thumbnail": result["images"][0]["url"],
        "name": result["name"],
        "description": description,
        "tracks": songs,
    }


# this route should be called by the client when they load the /spotify/plid/load page.
# it finds which songs don't have a TrackSource to download from (youtube, local),
# sends their IDs to the client, and queues youtube sourcing tasks.
@app.get("/spotify/{pl_id}/load")
async def spotify_playlist_load(pl_id: str):
    # get spotify playlist
    tracks = get_spotify_playlist(pl_id)["tracks"]
    resp = []

    # spotify tracksource -> trackmeta -> youtube tracksource
    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        for sp_track in tracks:
            spotify_source: TrackSource = await session.scalar(
                select(TrackSource)
                .where(
                    TrackSource.source == "spotify", TrackSource.id == sp_track["id"]
                )
                .options(  # No lazy loading with async!!
                    selectinload(TrackSource.track_meta).selectinload(TrackMeta.sources)
                )
            )

            if spotify_source:  # get Meta from existing tracksource
                meta = spotify_source.track_meta
            else:  # get Meta from get_or_create using artist+title
                meta = await TrackMeta.get_or_create(
                    session, sp_track["artists"][0], sp_track["title"]
                )

                # create new spotify Source and link to Meta
                spotify_source = TrackSource(
                    source="spotify",
                    id=sp_track["id"],
                    track_meta=meta,
                )
                session.add(spotify_source)
                await session.commit()

            # check if TM already has a download source for it
            await session.refresh(meta, ["sources"])

            local = next((s for s in meta.sources if s.source == "local"), None)
            youtube = next((s for s in meta.sources if s.source == "youtube"), None)

            source = local or youtube

            if not source:
                resp.append(
                    {"spotify_id": sp_track["id"], "meta_id": meta.id, "missing": True}
                )
                await yt_search_queue.put(meta)
            else:
                resp.append(
                    {"spotify_id": sp_track["id"], "meta_id": meta.id, "missing": False}
                )

    return resp


@app.get("/spotify/{pl_id}")
async def spotify_playlist(request: Request, pl_id: str):
    playlist = get_spotify_playlist(pl_id)
    playlist_meta = {
        "thumbnail": playlist["thumbnail"],
        "name": playlist["name"],
        "description": playlist["description"],
        "id": pl_id,
    }
    tracks_sp = playlist["tracks"]
    tracks_yt = []

    success = True

    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        for track in tracks_sp:
            spotify: TrackSource = await session.scalar(
                select(TrackSource)
                .where(TrackSource.source == "spotify", TrackSource.id == track["id"])
                .options(  # No lazy loading with async!!
                    selectinload(TrackSource.track_meta).selectinload(TrackMeta.sources)
                )
            )

            if not spotify:
                success = False
                break

            meta = spotify.track_meta

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
                success = False
                break

    if success:
        for track in tracks_yt:
            audio_status = -2
            if audio_exists(track["id"]):
                audio_status = -1

            track["status"] = audio_status

        return render(
            "playlist.html", request, videos=tracks_yt, playlist=playlist_meta
        )
    else:
        entries = []

        for entry in tracks_sp:  # pyright: ignore[reportGeneralTypeIssues]
            entries.append(
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "artist": entry["artists"][0],
                    "image": entry["image"][1]["url"],
                }
            )

        return render(
            "spotify_playlist_load.html",
            request,
            tracks=tracks_sp,
            playlist=playlist_meta,
        )
