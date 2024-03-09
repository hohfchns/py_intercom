from typing import Optional
import speech_recognition as sr
import logging as log

class VoiceParser:
    def __init__(self):
        pass

    def convert_voice_to_text(self, recognizer: sr.Recognizer, audio, language: str) -> tuple[str, int]:
        try:
            global CURRENT_LANGUAGE
            text = recognizer.recognize_google(audio, language=language)
            return (text, 0)
        except sr.UnknownValueError:
            return ("", 0)
        except sr.RequestError as e:
            return (f"Error; {e}", 1)

    def get_voice_data(self, recognizer: sr.Recognizer) -> object:
        with sr.Microphone() as mic:
            log.info("Listening...")

            recognizer.energy_threshold = 100
            try:
                data = recognizer.listen(mic, timeout=3, phrase_time_limit=10)
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

