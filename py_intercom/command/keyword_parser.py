from typing import Optional


class KeywordParser:
    def __init__(self, keyword_maps: dict[str,list[list[str]]]):
        self._keyword_maps: dict[str,list[list[str]]] = keyword_maps

    def parse(self, prompt: str) -> Optional[str]:
        for command_id in self._keyword_maps.keys():
            command_triggers = self._keyword_maps[command_id]
            for trigger in command_triggers:
                found = True
                for tw in trigger:
                    if tw.lower() not in prompt.lower():
                        found = False
                        break
                if found:
                    return command_id

        return None
    
    def set_keyword_maps(self, keyword_maps: dict[str,list[list[str]]]) -> None:
        self._keyword_maps = keyword_maps
    def get_keyword_maps(self) -> dict[str,list[list[str]]]:
        return self._keyword_maps

