from os import getenv

from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

from ..db import AsyncSessionLocal
from ..db.models import Cache

spotify = Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=getenv("spotify_client_id"),
        client_secret=getenv("spotify_client_secret"),
    )
)


async def get_spotify_playlist(playlist_id, no_update=False):
    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        cached_playlist = await Cache.get_content(session, "spotify", playlist_id)

    # immediately return cached playlist if caller wants no updates (only if it exists)
    if cached_playlist and no_update:
        return cached_playlist

    playlist = spotify.playlist(playlist_id)

    snapshot_id = playlist["snapshot_id"]

    # check if the cached playlist is the same as the spotify result
    if cached_playlist and cached_playlist["snapshot_id"] == snapshot_id:
        return cached_playlist

    songs = []
    tracks = playlist["tracks"]

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
            tracks = spotify.next(tracks)
        else:
            break

    description = playlist["description"]
    if description == "":
        description = (
            "this spotify playlist has no description. that's pretty lame dawg."
        )

    result = {
        "thumbnail": playlist["images"][0]["url"],
        "name": playlist["name"],
        "description": description,
        "tracks": songs,
        "snapshot_id": snapshot_id,
    }

    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        await Cache.set_content(session, "spotify", playlist_id, result)

    return result
