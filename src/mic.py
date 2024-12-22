"""Voice activity detection."""

import asyncio
import io
import logging
import time
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
MIN_DURATION = 0.5  # seconds
MAX_DECAY_COUNT = 30  # 30 frames * 30 ms = 0.9s
INI_DECAY_COUNT = -10  # 10 frames * 30 ms = 300ms


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
    """Generator that yields voice data as io.BytesIO."""
    stream = input_stream()
    vad = webrtcvad.Vad(VAD_AGRESSIVENESS)
    try:
        is_during = False

        buf = []
        decay_counter = INI_DECAY_COUNT

        def _reset():
            nonlocal buf, decay_counter
            buf.clear()
            decay_counter = INI_DECAY_COUNT

        async for block in stream:
            block = block[:, 0]
            is_speech = vad.is_speech(block.tobytes(), SAMPLE_RATE)

            if is_speech and not is_during:
                # log.info("Start voice!")
                is_during = True
                _reset()
            elif is_speech and is_during:
                decay_counter += 1
                decay_counter = min(decay_counter, MAX_DECAY_COUNT)
            elif not is_speech and is_during:
                decay_counter -= 1
                if decay_counter <= 0:
                    # log.info("End voice!")
                    is_during = False
                    wav = np.concatenate(buf).reshape(-1, 1)
                    _reset()

                    if len(wav) < int(MIN_DURATION * SAMPLE_RATE):
                        continue

                    file = io.BytesIO()
                    await asyncio.to_thread(
                        sf.write, file, wav, SAMPLE_RATE, format="flac"
                    )
                    file.seek(0)
                    yield file
            elif not is_speech and not is_during:
                pass

            if is_during:
                buf.append(block)

    except KeyboardInterrupt:
        pass


async def main():
    """Test entrypoint."""
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
