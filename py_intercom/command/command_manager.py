from typing import Optional
from py_intercom.command.keyword_parser import KeywordParser
from piney_event.event import TypedEvent
import logging as log

class CommandManager:
    callback_requested: TypedEvent = TypedEvent(str, str, dict)
    say: Optional[str] = None

    def __init__(self, command_map: dict={}):
        self._command_map: dict[str,dict[str,dict]] = {}
        self._parser_map: dict[str,KeywordParser] = {}
        self.set_command_map(command_map)
        
    def set_command_map(self, command_map: dict[str,dict[str,dict]]) -> None:
        self._command_map = command_map
        self._parser_map = {}
        for language in command_map.keys():
            minimal = {}
            for command_id in command_map[language].keys():
                minimal[command_id] = command_map[language][command_id].pop("triggers")
            self._parser_map[language] = KeywordParser(minimal)

    def get_command_map(self) -> dict[str,dict[str,dict]]:
        return self._command_map

    def execute(self, command_id: str, language: str) -> str:
        command: dict = self._command_map[language][command_id]
        if not command or not "callback" in command:
            return f"Command {command_id} not found"

        CommandManager.say = None

        CommandManager.callback_requested.emit(command_id, language, self._command_map)

        if CommandManager.say:
            return CommandManager.say

        return f"Command {command_id} executed."
    
    def parse_and_execute(self, prompt: str, language: str) -> Optional[str]:
        if language not in self._command_map:
            log.error(f"Current language `{language}` is not added in CommandManager")
            return None

        # breakpoint()
        log.debug(f"Attempting to parse prompt `{prompt}` for commands.")
        found = self._parser_map[language].parse(prompt)
        if found:
            log.debug(f"Found command `{found}`. Executing...")
            return self.execute(found, language)

        log.debug(f"No command found")
        return None

