from typing import Optional
from threading import Thread
from threading import Event as Flag
from py_intercom.tts.tts_wrapper import TTSWrapper
from py_intercom.voice.voice_parser import VoiceParser 
from py_intercom.command.command_manager import CommandManager
from helpers.openai_wrapper import GptWrapper
import logging as log
import time


class Intercom:
    def __init__(self, config: dict, command_map: dict[str,dict[str,dict]], voice_parser: VoiceParser = VoiceParser(), command_manager: CommandManager = CommandManager({})):
        self.config: dict = config
        self.language: str = self.config["default_language"]

        self._voice_parser: VoiceParser = voice_parser

        self._command_manager: CommandManager = command_manager
        self._command_manager.set_command_map(command_map)

        self._gpt: GptWrapper = GptWrapper()

        self._tts: TTSWrapper = TTSWrapper(self.config["tts"])

        self.main_loop: Optional[Thread] = None
        self.loop_should_stop: Flag = Flag()
        self.loop_should_stop.clear()

    def listen_for_prompt(self) -> str:
        try:
            prompt = self._voice_parser.listen(self.config["intercom"]["activation_keywords"][self.language], self.language)
            if prompt:
                return prompt
        except RuntimeError:
            return "Prompt not received"

        return ""
    
    def process_prompt(self, prompt: str) -> Optional[str]:
        return self._command_manager.parse_and_execute(prompt, self.language)

    def get_gpt_response(self, prompt: str) -> str:
        return self._gpt.get_response(prompt)
    
    def send_to_tts(self, text: str) -> None:
        self._tts.run(text, self.language)

    def start_main_loop(self) -> None:
        self.main_loop = Thread(target=self.main_loop_thread)
        self.main_loop.start()
        self.loop_should_stop.clear()

    def stop_main_loop(self) -> None:
        log.info("Stopping main loop")
        self.loop_should_stop.set()
    
    def main_loop_thread(self) -> None:
        self._exit_code = 0
        while True:
            if self.loop_should_stop.is_set():
                break
            try:
                prompt = self.listen_for_prompt()
                if not prompt:
                    continue

                log.info(f"Got voice prompt '{prompt}'")

                command = self.process_prompt(prompt)
                if command:
                    log.info(f"Sending command result `{command}` to TTS")
                    self.send_to_tts(command)
                    continue

                prompt_prepend = self.config["intercom"]["prompt_prepend"]
                current_language = self.config["intercom"]["prompt_language_map"][self.language]
                gpt_prompt = f"{prompt_prepend}. Speak to me in {current_language}. {prompt}"
                log.debug(f"Sending prompt `{gpt_prompt}` to GPT")

                gpt_response = self._gpt.get_response(gpt_prompt)
                log.debug(f"Got GPT response `{gpt_response}`")

                if not gpt_response:
                    log.debug(f"GPT response invalid, skipping TTS.")
                    continue

                self.send_to_tts(gpt_response)
            except Exception as e:
                self._exit_code = -1
                self.loop_should_stop.set()
                raise e

    def set_language(self, to: str) -> None:
        self.language = to
    def get_language(self) -> str:
        return self.language

    def get_exit_code(self) -> int:
        return self._exit_code


