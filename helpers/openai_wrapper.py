from openai import OpenAI
from typing import Optional

class GptWrapper:
    def __init__(self, api_key: Optional[str] = "", model: str = "gpt-3.5-turbo"):
        self.model = model
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = OpenAI()

    def get_response(self, prompt: str) -> str:
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "assistant", "content": prompt}],
            stream=True
        )

        response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content is not None:
                response += chunk.choices[0].delta.content

        return response


if __name__ == "__main__":
    gpt = GptWrapper()
    print(gpt.get_response("Hey GPT, how are you?"))


