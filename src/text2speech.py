"""Thanks ray."""
# import schedule
# import time


# def take_meds():
#     print("It's time to take your meds")
#     # play the pre-recorded audio file

# schedule.every().day.at("09:00").do(take_meds)
# schedule.every().day.at("13:00").do(take_meds)
# schedule.every().day.at("19:00").do(take_meds)
# while True:
#     schedule.run_pending()  # Checks and runs any jobs due at this moment
#     time.sleep(30)

from io import BytesIO

from gtts import gTTS


def speak_with_speed(text, language="en", tld=None):
    """Takes in text,language, and accent parameter."""
    mp3_fp = BytesIO()
    lang = language
    tld_compatible_langs = {
        "en",
        "com.au",
        "co.uk",
        "us",
        "ca",
        "co.in",
        "ie",
        "co.za",
        "com.ng",
    }
    if tld and lang in tld_compatible_langs:
        tts = gTTS(text=text, lang=lang, slow=False, tld=tld)
    else:  # for chinese, cuz chinese doesnt take tld = none. tld controls accent
        tts = gTTS(text=text, lang=lang, slow=False)

    tts.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return mp3_fp
    # audio = AudioSegment.from_file(mp3_fp, format="mp3")

    # if lang == "zh-CN":
    #     new_audio = audio.speedup(playback_speed=1.25)
    # elif lang == "en":
    #     new_audio = audio.speedup(playback_speed=1.1)

    # play(new_audio)


# Example usage
# speak_with_speed(text="KEEP GOING", language="en", tld="us")
# speak_with_speed("你妈妈没有毛",language="zh-CN", )
