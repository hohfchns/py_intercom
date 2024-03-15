import os
import tempfile
from pydub import AudioSegment
from pydub.playback import play
from gtts import gTTS

class TTSWrapper:
    def __init__(self, config: dict):
        self.config: dict = config

    def run(self, text: str, language: str) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tts = gTTS(text, lang=self.config["gtts_language_map"][language])
            out_file = os.path.join(tmpdir, "intercom_output.mp3")
            tts.save(out_file)
            sound = AudioSegment.from_mp3(out_file)
            play(sound)


if __name__ == "__main__":
    tts = TTSWrapper({
        "gtts_language_map": {
            "en_US": "en",
            "he_IL": "iw"
        }
    })

    tts.run("Hello, how are you today?", "en_US")
    tts.run("מה קורה אחשלי", "he_IL")

