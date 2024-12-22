"""Main entrypoint."""

import asyncio
import logging
import os

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

from .mic import voice_stream

load_dotenv()

AUTH = HTTPBasicAuth("user", os.getenv("TOKEN"))
URL = "https://wth.interpause.dev"

log = logging.getLogger(__name__)


def system_prompt():
    """System prompt."""
    # TODO: select language.
    return [
        {
            "role": "system",
            "content": "You can communicate in both English and Chinese.",
        },
        {
            "role": "assistant",
            "content": "Hello, how can I help you?",
        },
    ]


async def get_response(file, history):
    """Get response from server."""
    files = {"file": file}
    upload_resp = await asyncio.to_thread(
        requests.post, f"{URL}/upload_audio/", files=files, auth=AUTH
    )
    audio_id = upload_resp.json().get("audio_id")
    convo = history + [
        {"role": "user", "content": [{"type": "audio", "audio_id": audio_id}]}
    ]
    gen_resp = await asyncio.to_thread(
        requests.post, f"{URL}/generate", json=convo, auth=AUTH
    )
    model_text = gen_resp.json().get("response")
    convo.append({"role": "assistant", "content": model_text})
    return model_text, convo


async def main():
    """Main."""
    logging.basicConfig(level=logging.INFO)
    history = system_prompt()

    can_listen = True

    def _task_done(future: asyncio.Future):
        nonlocal history, can_listen
        model_text, convo = future.result()
        history = convo
        log.info(history)
        log.info(model_text)
        can_listen = True

    req_queue = []
    try:
        # get audio clips
        async for file in voice_stream():
            if not can_listen:
                continue
            can_listen = False
            log.info("Got audio clip.")
            task = asyncio.create_task(get_response(file, history))
            task.add_done_callback(_task_done)
            req_queue.append(task)

    except KeyboardInterrupt:
        while len(req_queue) > 0:
            task = req_queue.pop()
            await task
        return


if __name__ == "__main__":
    asyncio.run(main())
