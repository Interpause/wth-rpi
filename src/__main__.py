"""Main entrypoint."""

import asyncio
import logging
import os
import time

import requests
import uvloop
from dotenv import load_dotenv
from pydub import AudioSegment
from pydub.playback import play
from requests.auth import HTTPBasicAuth

from src.text2speech import speak_with_speed

from .mic import voice_stream

load_dotenv()

AUTH = HTTPBasicAuth("user", os.getenv("TOKEN"))
URL = "https://wth.interpause.dev"
IS_CHINESE = False
ENGLISH_SPEED = 1.5
CHINESE_SPEED = 2.0

log = logging.getLogger(__name__)


def system_prompt():
    """System prompt."""
    # TODO: select language.
    return [
        {
            "role": "system",
            "content": "You can communicate in both English and Chinese. As a direct sound2text model, you are also further able to understand sounds, including guessing the gender and emotions of a person based their voice.",
        },
        {
            "role": "assistant",
            "content": "Hello, how can I help you?",
        },
    ]


def get_response(file, history):
    """Get response from server."""
    files = {"file": file}
    upload_resp = requests.post(f"{URL}/upload_audio/", files=files, auth=AUTH)
    audio_id = upload_resp.json().get("audio_id")
    convo = history + [
        {"role": "user", "content": [{"type": "audio", "audio_id": audio_id}]}
    ]
    gen_resp = requests.post(f"{URL}/generate", json=convo, auth=AUTH)
    model_text = gen_resp.json().get("response")
    convo.append({"role": "assistant", "content": model_text})
    return model_text, convo


async def main():
    """Main."""
    logging.basicConfig(level=logging.INFO)

    history = system_prompt()
    can_listen = True

    def _task(file, convo):
        nonlocal history, can_listen
        model_text, convo = get_response(file, convo)
        history = convo
        log.info(history)
        log.info(model_text)
        tts_mp3 = speak_with_speed(model_text, language="en")
        audio = AudioSegment.from_file(tts_mp3, format="mp3")
        audio = audio.speedup(
            playback_speed=CHINESE_SPEED if IS_CHINESE else ENGLISH_SPEED
        )
        play(audio)
        time.sleep(1)
        can_listen = True

    req_queue = []
    try:
        log.info("Listening.")
        # get audio clips
        async for file in voice_stream():
            if not can_listen:
                continue
            can_listen = False
            log.info("Got audio clip.")
            task = asyncio.create_task(asyncio.to_thread(_task, file, history))
            req_queue.append(task)

    except KeyboardInterrupt:
        while len(req_queue) > 0:
            task = req_queue.pop()
            await task
        return


if __name__ == "__main__":
    uvloop.install()
    asyncio.run(main())
