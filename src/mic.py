"""Voice activity detection."""

import asyncio
import io
import logging
from typing import AsyncGenerator

import numpy as np
import sounddevice as sd
import soundfile as sf
import webrtcvad

log = logging.getLogger(__name__)

SAMPLE_RATE = 48000
FRAME_SIZE = 30  # ms, either 10, 20, or 30
BLOCK_SIZE = int(SAMPLE_RATE * FRAME_SIZE / 1000)  # samples
VAD_AGRESSIVENESS = 3  # 0 to 3


async def input_stream() -> AsyncGenerator[np.ndarray, None]:
    """Generator that yields blocks of input data as np.array."""
    q_in = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def _cb(block, frame_count, time_info, status):
        loop.call_soon_threadsafe(q_in.put_nowait, (block.copy(), status))

    stream = sd.InputStream(
        callback=_cb,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        channels=1,
        dtype="int16",
    )
    with stream:
        while True:
            block, status = await q_in.get()
            if status:
                log.warning("Error: %s", status)
            yield block


async def voice_stream() -> AsyncGenerator[io.BytesIO, None]:
    stream = input_stream()
    vad = webrtcvad.Vad(VAD_AGRESSIVENESS)
    try:
        is_during = False
        buf = []
        async for block in stream:
            block = block[:, 0]
            is_speech = vad.is_speech(block.tobytes(), SAMPLE_RATE)

            if is_speech and not is_during:
                log.info("Start voice!")
                is_during = True
                buf.clear()
            elif is_speech and is_during:
                pass
            elif not is_speech and is_during:
                log.info("End voice!")
                is_during = False

                # upload code
                wav = np.concatenate(buf).reshape(-1, 1)
                buf.clear()
                file = io.BytesIO()
                sf.write(file, wav, SAMPLE_RATE, format="flac")
                file.seek(0)
                yield file
            elif not is_speech and not is_during:
                pass

            if is_during:
                buf.append(block)

    except KeyboardInterrupt:
        pass


async def main():
    logging.basicConfig(level=logging.INFO)

    can_play = False

    async def _play_skip(data, sr):
        nonlocal can_play
        if can_play:
            return
        can_play = True
        await asyncio.to_thread(sd.play, data, sr, blocking=True)
        await asyncio.sleep(2)
        can_play = False

    play_reqs = []

    async for file in voice_stream():
        data, sr = sf.read(file)

        if not can_play:
            play_reqs.append(asyncio.create_task(_play_skip(data, sr)))

    while len(play_reqs) > 0:
        task = play_reqs.pop()
        await task


if __name__ == "__main__":
    asyncio.run(main())
