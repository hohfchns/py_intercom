import logging as log
from time import sleep
from typing import Optional
from threading import Thread
from threading import Event as Flag
from py_intercom.networking.intercom_server import IntercomServer
from py_intercom.tts.tts_wrapper import TTSWrapper
from py_intercom.voice.voice_parser import VoiceParser 
from py_intercom.command.command_manager import CommandManager
from helpers.openai_wrapper import GptWrapper
from piney_event.event import TypedEvent

class Intercom:
    def __init__(self, config: dict, command_map: dict[str,dict[str,dict]], voice_parser: Optional[VoiceParser] = None, command_manager: CommandManager = CommandManager({})):
        self.command_requested: TypedEvent = TypedEvent(str, str, dict)

        self.config: dict = config
        self.language: str = self.config["intercom"]["default_language"]

        self.is_networked: bool = self.config["networking"]["is_networked"] if "networking" in self.config and "is_networked" in self.config["networking"] else False
        self.server_ip: Optional[str] = None
        self.server_manager: Optional[IntercomServer] = None
        self.is_server: bool = False
        if self.is_networked:
            self.server_manager = IntercomServer()
            self.is_server = self.config["networking"]["is_server"] if "is_server" in self.config["networking"] else False
            if self.is_server:
                log.info("Starting Intercom server")
                self.server_ip = self.server_manager.start_server()
            else:
                self.server_ip = self.config["networking"]["server_ip"]
                if IntercomServer.test_connection(self.server_ip):
                    log.info(f"Server at `{self.server_ip}` is available")
                else:
                    raise RuntimeError(f"Could not establish intercom as there is no valid server at `{self.server_ip}`")
                sleep(1)
                log.info(f"Starting Intercom client, connecting to ip `{self.server_ip}`")
                self.server_manager.start_client(self.server_ip)

            self.server_manager.received_message_from_server.connect(self._on_received_message_from_server)

        if voice_parser:
            self._voice_parser: VoiceParser = voice_parser
        else:
            self._voice_parser: VoiceParser = VoiceParser(
                self.config["voice"]["energy_threshold"],
                self.config["voice"]["timeout"],
                self.config["voice"]["phrase_time_limit"],
                self.config["voice"]["adjust_for_ambient_noise"]
            )

        self._command_manager: CommandManager = command_manager
        self._command_manager.set_command_map(command_map)
        CommandManager.callback_requested.connect(self._on_command_requested)

        self._gpt: GptWrapper = GptWrapper()

        self._tts: TTSWrapper = TTSWrapper(self.config["tts"])
        self._tts_queue: list[str] = []

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
        log.debug(f"Sending text {text} to TTS")
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
            if self.is_networked and self.server_manager and not self.server_manager.is_running():
                self.stop_main_loop()
                break
            if self.loop_should_stop.is_set():
                break
            try:
                if self.is_networked and not self.is_server:
                    continue

                while len(self._tts_queue):
                    self.send_to_tts(self._tts_queue.pop())

                prompt = self.listen_for_prompt()
                if not prompt:
                    continue

                log.info(f"Got voice prompt '{prompt}'")

                command = self.process_prompt(prompt)
                # This will be handled in the _confirm_command event callback
                if command:
                    continue

                prompt_prepend = self.config["intercom"]["prompt_prepend"]
                current_language = self.config["intercom"]["prompt_language_map"][self.language]
                gpt_prompt = f"{prompt_prepend}. Speak to me in {current_language}. {prompt}"
                log.info(f"Sending prompt `{gpt_prompt}` to GPT")

                gpt_response = self._gpt.get_response(gpt_prompt)
                log.info(f"Got GPT response `{gpt_response}`")

                if not gpt_response:
                    log.info(f"GPT response invalid, skipping TTS.")
                    continue

                self.send_to_tts(gpt_response)
            except Exception as e:
                self._exit_code = -1
                self.loop_should_stop.set()
                raise e

    def _confirm_command(self, command_id: str, language: str, command_map: dict) -> None:
        CommandManager.say = None
        self.command_requested.emit(command_id, language, command_map)
        if CommandManager.say:
            self._tts_queue.append(CommandManager.say)

    def _on_command_requested(self, command_id: str, language: str, command_map: dict) -> None:
        command = command_map[language][command_id]
        is_networked = command["is_remote"] if "is_remote" in command else False
        if not is_networked or not self.server_manager:
            log.debug(f"Intercom confirmed local command `{command_id}`")
            self._confirm_command(command_id, language, command_map)
            return

        if not "remote_address" in command:
            log.error(f"Missing configuration parameter `remote_address` for command `{command_id}`")
            return
        
        data = {"command_id": command_id, "command_map": command_map, "language": language}

        ip: str = command["remote_address"]

        local_exec = command["remote_and_local"] if "remote_and_local" in command else False
        if local_exec:
            self._confirm_command(command_id, language, command_map)

        log.info(f"Sending command `{command_id}` to ip `{ip}`")
        self.server_manager.send_data(data, ip, kind="command")

    def _on_received_message_from_server(self, message: IntercomServer.Message) -> None:
        log.debug(f"Received message from server | {message}")
        if message.kind != "command":
            return
        
        command_id = message.data["command_id"]
        command_map = message.data["command_map"]
        language = message.data["language"]
        self._confirm_command(command_id, language, command_map)

    def set_language(self, to: str) -> None:
        self.language = to
    def get_language(self) -> str:
        return self.language

    def get_exit_code(self) -> int:
        return self._exit_code


