from typing import Optional
import speech_recognition as sr
import logging as log

class VoiceParser:
    def __init__(self, energy_threshold: int = 100, timeout: float = 3.0, phrase_time_limit: float = 10, adjust_for_ambient_noise: bool = False):
        self.energy_threshold = energy_threshold
        self.timeout = timeout
        self.phrase_time_limit = phrase_time_limit
        self.adjust_for_ambient_noise = adjust_for_ambient_noise

    def convert_voice_to_text(self, recognizer: sr.Recognizer, audio, language: str) -> tuple[str, int]:
        try:
            text = recognizer.recognize_google(audio, language=language)
            return (text, 0)
        except sr.UnknownValueError:
            return ("", 0)
        except sr.RequestError as e:
            return (f"Error; {e}", 1)

    def get_voice_data(self, recognizer: sr.Recognizer) -> object:
        with sr.Microphone() as mic:
            log.info("Listening...")

            recognizer.energy_threshold = self.energy_threshold
            try:
                if self.adjust_for_ambient_noise:
                    recognizer.adjust_for_ambient_noise(mic)
                data = recognizer.listen(mic, timeout=self.timeout, phrase_time_limit=self.phrase_time_limit)
            except sr.WaitTimeoutError:
                data = None
            except Exception as e:
                log.error(e)
                raise RuntimeError

            log.info("Got audio.")
            return data

    def listen(self, trigger_words:list[str], language: str, recognizer: sr.Recognizer = sr.Recognizer()) -> str:
        prompt: str = ""

        def should_trigger(words, prompt) -> bool:
            for w in words:
                if w not in prompt:
                    return False
            return True

        while not should_trigger(trigger_words, prompt.lower()):
            voice = self.get_voice_data(recognizer)
            if voice == None:
                log.info("Audio not recognizable")
                continue

            prompt, err = self.convert_voice_to_text(recognizer, voice, language)

            if err != 0:
                err_str = f"Parsing voice data received error {err}: `{prompt}`"
                raise RuntimeError(err_str)
            
        return prompt

