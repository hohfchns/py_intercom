import logging as log
from time import sleep
from typing import Optional
from threading import Thread
from threading import Event as Flag
from py_intercom.networking.intercom_server import IntercomServer
from py_intercom.tts.tts_wrapper import TTSWrapper
from py_intercom.voice.voice_parser import VoiceParser 
from py_intercom.command.command_manager import CommandManager
from py_intercom.llm.llm import LLM
from piney_event.event import TypedEvent

class Intercom:
    def __init__(self, config: dict, command_map: dict[str,dict[str,dict]], voice_parser: Optional[VoiceParser] = None, command_manager: CommandManager = CommandManager({})):
        self.command_requested: TypedEvent = TypedEvent(str, str, dict)

        self._config: dict = config
        self._language: str = self._config["intercom"]["default_language"]

        self._is_networked: bool = self._config["networking"]["is_networked"] if "networking" in self._config and "is_networked" in self._config["networking"] else False
        self._server_ip: Optional[str] = None
        self._server_manager: Optional[IntercomServer] = None
        self._is_server: bool = False
        if self._is_networked:
            self._server_manager = IntercomServer()
            self._is_server = self._config["networking"]["is_server"] if "is_server" in self._config["networking"] else False
            if self._is_server:
                log.info("Starting Intercom server")
                self._server_ip = self._server_manager.start_server()
            else:
                self._server_ip = self._config["networking"]["server_ip"]
                if IntercomServer.test_connection(self._server_ip):
                    log.info(f"Server at `{self._server_ip}` is available")
                else:
                    raise RuntimeError(f"Could not establish intercom as there is no valid server at `{self._server_ip}`")
                sleep(1)
                log.info(f"Starting Intercom client, connecting to ip `{self._server_ip}`")
                self._server_manager.start_client(self._server_ip)

            self._server_manager.received_message_from_server.connect(self._on_received_message_from_server)

        if voice_parser:
            self._voice_parser: VoiceParser = voice_parser
        else:
            self._voice_parser: VoiceParser = VoiceParser(
                self._config["voice"]["energy_threshold"],
                self._config["voice"]["timeout"],
                self._config["voice"]["phrase_time_limit"],
                self._config["voice"]["adjust_for_ambient_noise"]
            )

        self._command_manager: CommandManager = command_manager
        self._command_manager.set_command_map(command_map)
        CommandManager.callback_requested.connect(self._on_command_requested)

        llm_type: str = "gemini"
        conversation_starter: str = "Your name is Intercom. You are an AI assistant."
        model: Optional[str] = None
        if "ai" in config:
            if "type" in config["ai"]:
                llm_type = config["ai"]["type"]
            if "conversation_starter" in config["ai"]:
                conversation_starter = config["ai"]["conversation_starter"]
            if "model" in config["ai"]:
                model = config["ai"]["model"]

        t = LLM.Type.from_str(llm_type)
        self._llm: LLM = LLM(t if t else LLM.Type.GEMINI, conversation_starter, model_name=model)
        self._llm.start_conversation()

        self._tts: TTSWrapper = TTSWrapper(self._config["tts"])
        self._tts_queue: list[str] = []

        self._main_loop: Optional[Thread] = None
        self._loop_should_stop: Flag = Flag()
        self._loop_should_stop.clear()

    def listen_for_prompt(self) -> str:
        try:
            prompt = self._voice_parser.listen(self._config["intercom"]["activation_keywords"][self._language], self._language)
            if prompt:
                return prompt
        except RuntimeError:
            return "Prompt not received"

        return ""
    
    def process_prompt(self, prompt: str) -> Optional[str]:
        return self._command_manager.parse_and_execute(prompt, self._language)

    def get_ai_response(self, prompt: str) -> str:
        return self._llm.get_response(prompt)
    
    def send_to_tts(self, text: str) -> None:
        log.debug(f"Sending text {text} to TTS")
        self._tts.run(text, self._language)

    def start_main_loop(self) -> None:
        self._main_loop = Thread(target=self.main_loop_thread)
        self._main_loop.start()
        self._loop_should_stop.clear()

    def stop_main_loop(self) -> None:
        log.info("Stopping main loop")
        self._loop_should_stop.set()
    
    def main_loop_thread(self) -> None:
        self._exit_code = 0
        while True:
            if self._is_networked and self._server_manager and not self._server_manager.is_running():
                self.stop_main_loop()
                break
            if self._loop_should_stop.is_set():
                break
            try:
                if self._is_networked and not self._is_server:
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

                prompt_prepend = self._config["intercom"]["prompt_prepend"] if "prompt_prepend" in self._config["intercom"] else ""
                current_language = self._config["intercom"]["prompt_language_map"][self._language]
                ai_prompt = f"{prompt_prepend}. Speak to me in {current_language}. {prompt}"
                log.info(f"Sending prompt `{ai_prompt}` to LLM")

                ai_response = self.get_ai_response(ai_prompt)
                log.info(f"Got LLM response `{ai_response}`")

                if not ai_response:
                    log.info(f"LLM response invalid, skipping TTS.")
                    continue

                self.send_to_tts(ai_response)
            except Exception as e:
                self._exit_code = -1
                self._loop_should_stop.set()
                raise e

    def _confirm_command(self, command_id: str, language: str, command_map: dict) -> None:
        CommandManager.say = None
        self.command_requested.emit(command_id, language, command_map)
        if CommandManager.say:
            self._tts_queue.append(CommandManager.say)

    def _on_command_requested(self, command_id: str, language: str, command_map: dict) -> None:
        command = command_map[language][command_id]
        is_networked = command["is_remote"] if "is_remote" in command else False
        if not is_networked or not self._server_manager:
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
        self._server_manager.send_data(data, ip, kind="command")

    def _on_received_message_from_server(self, message: IntercomServer.Message) -> None:
        log.debug(f"Received message from server | {message}")
        if message.kind != "command":
            return
        
        command_id = message.data["command_id"]
        command_map = message.data["command_map"]
        language = message.data["language"]
        self._confirm_command(command_id, language, command_map)

    def set_language(self, to: str) -> None:
        self._language = to
    def get_language(self) -> str:
        return self._language

    def get_config(self) -> dict:
        return self._config

    def get_exit_code(self) -> int:
        return self._exit_code


