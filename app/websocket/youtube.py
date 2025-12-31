from .. import audio_queue, sio, video_queue
from ..util.youtube import audio_exists, video_exists


@sio.event
async def request_audios(sid, data):
    videos = data.get("video_id")

    tasks = []

    for video_id in videos:
        if audio_exists(video_id) or audio_queue.contains(video_id):
            return  # we already have it vro...

        was_empty = audio_queue.empty()
        await audio_queue.put(video_id)

        position = 0 if was_empty else audio_queue.qsize()

        tasks.append({"video_id": video_id, "position": position})

    await sio.emit("tasks_enqueued", {"type": "request_audio", "tasks": tasks}, to=sid)


@sio.event
async def request_videos(sid, data):
    video_id = data.get("video_id")

    if video_exists(video_id) or video_queue.contains(video_id):
        return  # we already have it vro...

    was_empty = video_queue.empty()
    await video_queue.put(video_id)

    position = 0 if was_empty else video_queue.qsize()

    await sio.emit(
        "tasks_enqueued",
        {
            "type": "request_video",
            "tasks": [{"video_id": video_id, "position": position}],
        },
        to=sid,
    )
