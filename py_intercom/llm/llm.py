from enum import Enum 
from typing import Optional
import logging as log

from helpers.openai_wrapper import GptWrapper
from helpers.gemini_wrapper import GeminiWrapper

class LLM:
    class Type(Enum):
        GPT = 0
        GEMINI = 1

        @staticmethod
        def from_str(string: str) -> Optional['LLM.Type']:
            if string.lower() == "gpt":
                return LLM.Type.GPT
            elif string.lower() == "gemini":
                return LLM.Type.GEMINI
            return None

    def __init__(self, llm_type: Type, conversation_starter: str, model_name: Optional[str] = None, api_key: Optional[str] = None):
        """
        :param llm_type: Which supported LLM to use.
        :param conversation_starter: The message that will be sent to the LLM when starting a new conversation.
        :param model_name: The specific model name, if None default is used. Examples would be `gemini-pro`, `gpt-3.5-turbo`, `gpt-4`, etc.
        """
        self._llm_type: LLM.Type = llm_type
        self._llm: GeminiWrapper | GptWrapper # Type definition for self._llm
        self._conversation_starter = conversation_starter
        self._model_name = model_name
        self._api_key = api_key

        if self._llm_type == LLM.Type.GPT:
            log.info(f"Creating new GPT model")
            if model_name:
                self._llm = GptWrapper(model=model_name, api_key=api_key)
            else:
                self._llm = GptWrapper(api_key=api_key)
        if self._llm_type == LLM.Type.GEMINI:
            log.info(f"Creating new Gemini model")
            if model_name:
                self._llm = GeminiWrapper(model=model_name, api_key=api_key)
            else:
                self._llm = GeminiWrapper(api_key=api_key)

    def start_conversation(self) -> str:
        if isinstance(self._llm, GeminiWrapper):
            response = self._llm.start_conversation(self._conversation_starter)
            return response if response else "" # Since we provide the argument, we should always get a string anyway
        elif isinstance(self._llm, GptWrapper):
            response = self._llm.get_response(self._conversation_starter)
            return response
        return ""
    
    def get_response(self, prompt: str) -> str:
        if isinstance(self._llm, GeminiWrapper):
            response = self._llm.get_response(prompt)
            return response if response else "" # Since we provide the argument, we should always get a string anyway
        elif isinstance(self._llm, GptWrapper):
            response = self._llm.get_response(prompt)
            return response
        return ""


