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
from lingua import Language, LanguageDetectorBuilder
from langcodes import standardize_tag

from src.text2speech import speak_with_speed

from .mic import voice_stream

load_dotenv()

AUTH = HTTPBasicAuth("user", os.getenv("TOKEN"))
URL = "https://wth.interpause.dev"
IS_CHINESE = True
SPEED = 1.2

log = logging.getLogger(__name__)


def system_prompt():
    """System prompt."""
    # TODO: select language.
    path = "/home/wth/DTI_catbot/wth-rpi/ch-prompt.txt" if IS_CHINESE else "/home/wth/DTI_catbot/wth-rpi/en-prompt.txt"
    with open(path, "r") as f:
        txt = f.read()
    return [
        {
            "role": "system",
            "content": txt,
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

    detector = LanguageDetectorBuilder.from_languages(
        Language.ENGLISH,
        Language.JAPANESE,
        Language.CHINESE,
        Language.KOREAN,
        Language.MALAY,
        Language.TAMIL,
    ).with_preloaded_language_models().build()

    history = system_prompt()
    can_listen = True

    def _task(file, convo):
        nonlocal history, can_listen
        model_text, convo = get_response(file, convo)
        history = convo
        log.info(history)
        log.info(model_text)
        lang = detector.detect_language_of(model_text)
        lang = standardize_tag(lang.iso_code_639_3.name)
        tts_mp3 = speak_with_speed(model_text, language=lang)
        audio = AudioSegment.from_file(tts_mp3, format="mp3")
        audio = audio.speedup(playback_speed=SPEED)
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
