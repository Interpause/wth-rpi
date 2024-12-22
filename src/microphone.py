import torch
import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write
from pydub import AudioSegment
import os

def load_silero_vad():
    model_path = "/Users/magentaong/VScode/WTH/silero-vad"
    model, utils = torch.hub.load(repo_or_dir=model_path, model='silero_vad', source='local',trust_repo=True)
    (get_speech_timestamps, save_audio, read_audio, VADIterator, collect_chunks) = utils
    return model, get_speech_timestamps, read_audio


def voice_activated_recording(filename, duration=10, samplerate=16000):
    print("Loading Silero model...")
    model, get_speech_timestamps, read_audio = load_silero_vad()
    print("Model loaded. Listening for voice...")

    audio_data = []
    def callback(indata, status):
        if status:
            print(status)
        audio_data.append(indata.copy())


    with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16', callback=callback):
        sd.sleep(duration * 1000)  # Duration to listen


    recorded_audio = np.concatenate(audio_data, axis=0)
    recorded_audio = recorded_audio.flatten()


    wav_file = filename + ".wav"
    write(wav_file, samplerate, recorded_audio)
    print(f"Raw audio saved as {wav_file}")

    
    audio = read_audio(wav_file, sampling_rate=samplerate)
    speech_timestamps = get_speech_timestamps(audio, model, sampling_rate=samplerate)

    if speech_timestamps:
        print(f"Detected speech in {len(speech_timestamps)} segment(s). Saving voice-only audio...")
        voice_audio = np.concatenate([audio[start:end] for start, end in [(ts['start'], ts['end']) for ts in speech_timestamps]])
        voice_wav_file = filename + "_voice.wav"
        write(voice_wav_file, samplerate, voice_audio)
        print(f"Voice-only audio saved as {voice_wav_file}")

        mp3_file = filename + ".mp3"
        audio_segment = AudioSegment.from_wav(voice_wav_file)
        audio_segment.export(mp3_file, format="mp3")
        print(f"Voice-only MP3 saved as {mp3_file}")
    else:
        print("No speech detected.")

voice_activated_recording("voice_recording", duration=10)
