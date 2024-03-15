import os
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.generativeai import ChatSession
from typing import Optional

GOOGLE_API_KEY: str = ""

class GeminiWrapper:
  def __init__(self, model: str = "gemini-pro", api_key: Optional[str] = None):
    global GOOGLE_API_KEY
    if not GOOGLE_API_KEY or api_key != GOOGLE_API_KEY:
      api_key = os.getenv('GOOGLE_API_KEY')
      if not api_key:
          raise RuntimeError("Please set the `GOOGLE_API_KEY` environment variable or provide the `api_key` argument to use gemini.")
      GOOGLE_API_KEY = api_key
      genai.configure(api_key=GOOGLE_API_KEY)

    self.model: GenerativeModel = GenerativeModel(model)
    self.chat: Optional[ChatSession] = None

  def get_response(self, text: str) -> str:
    if self.chat:
      response = self.chat.send_message(text)
    else:
      response = self.model.generate_content(text)
    return response.text
  
  def start_conversation(self, starter: Optional[str] = None) -> Optional[str]:
    self.chat = self.model.start_chat()
    if starter:
      return self.get_response(starter)
    return None


if __name__ == "__main__":
  gemini = GeminiWrapper()
  print(gemini.start_conversation("Hey! How are you?"))
  print(gemini.get_response("Can you repeat your last message?"))
  print(gemini.get_response("What is the current time in Israel?"))


