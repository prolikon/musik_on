from Levenshtein import ratio
from ytmusicapi import YTMusic

from .. import sio
from ..db import AsyncSessionLocal
from ..db.models import TrackMeta, TrackSource
from ..util.string import extract_script_segments


def evaluate(target, candidate):
    target = target.lower()
    candidate = candidate.lower()

    score = ratio(target, candidate)

    groups = extract_script_segments(candidate)

    for group in groups:
        group_score = ratio(target, group)
        score = max(score, group_score)

    return score


ytmusic = YTMusic()


async def find_youtube_tracksource(meta: TrackMeta):
    query = f"{meta.artist} - {meta.title}"
    print(query)

    songs = ytmusic.search(
        query=query,
        filter="songs",
        limit=1,
        ignore_spelling=True,
    )

    videos = ytmusic.search(
        query=query,
        filter="videos",
        limit=1,
        ignore_spelling=True,
    )

    song_valid = len(songs) > 0 and songs[0].get("videoId") is not None
    video_valid = len(videos) > 0 and videos[0].get("videoId") is not None

    match (song_valid, video_valid):
        case (False, False):
            raise Exception(f"No results found for [{query}]")
        case (False, True):
            result = videos[0]
        case (True, False):
            result = songs[0]
        case (True, True):
            song = songs[0]
            video = videos[0]

            score_song = evaluate(meta.artist, song["artists"][0]["name"])
            score_song += evaluate(meta.title, song["title"])
            score_video = evaluate(meta.artist, video["artists"][0]["name"])
            score_video += evaluate(meta.title, video["title"])
            # Use the one that evaluates to a higher match score
            result = score_song >= score_video and song or video

    video_id = result.get("videoId")

    async with AsyncSessionLocal() as session:  # pyright: ignore[reportGeneralTypeIssues]
        # create new youtube Source and link to Meta
        youtube_source = TrackSource(
            source="youtube",
            id=video_id,
            track_meta=meta,
        )
        session.add(youtube_source)
        await session.commit()

    await sio.emit(
        "task_complete",
        {"task": "youtube_source", "meta_id": youtube_source.track_meta_id},
    )
