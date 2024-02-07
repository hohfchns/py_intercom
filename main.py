import sys
import os
import subprocess
import shutil
import speech_recognition as sr
from enum import Enum

class PromptType(Enum):
    USER = 0,
    COMMAND = 1,
    JUNK = 2


PIPER_LANGS = [ "en_US" ]
GTTS_LANGS = [ "he_IL" ]

GTTS_LANG_FORMAT_MAP = {
    "he_IL": "iw"
}

KEYWORDS = \
{
    "en_US": ["intercom"],
    "he_IL": ["אינטרקום"]
}

COMMANDS = \
{
    "en_US": [
        {
            "command": "set_language",
            "params": ["he_IL"],
            "generic_name": "Hebrew",
            "triggers": [
              ["set", "language", "hebrew"],
              ["change", "language", "hebrew"],
            ]
        },
        {
            "command": "turn_off",
            "triggers": [
                ["turn", "off"],
                ["shut", "yourself" "off"],
                ["shut", "yourself" "down"],
            ]
        }
    ],
    "he_IL": [
        {
            "command": "set_language",
            "generic_name": "English",
            "params": ["en_US"],
            "triggers": [
                ["שנה", "שפה", "ל", "אנגלית"],
                ["חליף", "שפה", "ל", "אנגלית"],
            ]
        },
        {
            "command": "turn_off",
            "triggers": [
                ["תכבה", "את", "עצמך"],
                ["תסגור", "את", "עצמך"],
            ]
        }
    ]
}

CURRENT_LANGUAGE = "en_US"

shut_down_requested: bool = False

class CommandsInterface():
    @staticmethod
    def execute_command(method_name: str, method_params: list):
        command_function = getattr(CommandsInterface, method_name)
        print(f"Executing command `{method_name}` with params `{method_params}`")
        return command_function(*method_params)

    @staticmethod
    def set_language(to: str) -> str:
        global CURRENT_LANGUAGE
        generic_name = COMMANDS[CURRENT_LANGUAGE][0]["generic_name"]
        CURRENT_LANGUAGE = to
        return f"Setting language to {generic_name}"

    @staticmethod
    def turn_off() -> str:
        global shut_down_requested
        shut_down_requested = True
        return f"Shutting down"

def convert_voice_to_text(recognizer: sr.Recognizer, audio) -> tuple[str, int]:
    try:
        global CURRENT_LANGUAGE
        text = recognizer.recognize_google(audio, language=CURRENT_LANGUAGE)
        return (text, 0)
    except sr.UnknownValueError:
        return ("", 0)
    except sr.RequestError as e:
        return (f"Error; {e}", 1)

def get_voice_data(recognizer: sr.Recognizer) -> object:
    with sr.Microphone() as mic:
        print("Listening...")

        recognizer.energy_threshold = 100
        try:
            data = recognizer.listen(mic, timeout=3, phrase_time_limit=10)
        except sr.WaitTimeoutError:
            data = None
        except Exception:
            print(e)
            raise RuntimeError

        print("Got audio.")
        return data
        

def wait_for_voice_prompt(recognizer: sr.Recognizer, trigger_words:list[str]=[]) -> tuple[str, PromptType]:
    prompt: str = ""

    def find_command(prompt) -> tuple[str, list]:
        global CURRENT_LANGUAGE
        for command in COMMANDS[CURRENT_LANGUAGE]:
            for trigger in command["triggers"]:
                valid = True
                for tw in trigger:
                    if not tw.lower() in prompt.lower():
                        valid = False
                        continue

                if valid:
                    params = command["params"] if "params" in command else []
                    return command["command"], params

        return "", []

    def should_trigger(words, prompt) -> bool:
        for w in words:
            if not (w in prompt):
                return False
        return True

    while not should_trigger(trigger_words, prompt.lower()):
        voice = get_voice_data(recognizer)
        if voice == None:
            return "", PromptType.JUNK

        prompt, err = convert_voice_to_text(recognizer, voice)

        if err != 0:
            err_str = f"Parsing voice data received error {err}: `{prompt}`"
            raise RuntimeError(err_str)

        cmd, cmd_params = find_command(prompt)
        if cmd:
            print(f"Received command `{cmd}`")
            response = CommandsInterface.execute_command(cmd, cmd_params)
            if response:
                return response, PromptType.COMMAND
            else:
                return f"Command `{cmd}` executed.", PromptType.COMMAND
        else:
            print(f"Received prompt `{prompt}`")

    return prompt, PromptType.USER

def main(argv) -> int:
    if sys.platform != "linux":
        print("Only available on Linux OS")
        return 1

    gpt_cmd = "chatgpt"
    if shutil.which(gpt_cmd) == None:
        print(f"ChatGPT command `{gpt_cmd}` not installed?", file=sys.stderr)
        return 1

    subprocess.check_call(f"{gpt_cmd} --clear-history", shell=True)

    gtts_cmd = "gtts-cli"
    if shutil.which(gtts_cmd) == None:
        print(f"ChatGPT command `{gtts_cmd}` not installed?", file=sys.stderr)
        return 1

    piper_cmd = "piper-tts"
    if shutil.which(piper_cmd) == None:
        print(f"ChatGPT command `{piper_cmd}` not installed?", file=sys.stderr)
        return 1

    play_cmd = "play"
    if shutil.which(play_cmd) == None:
        print(f"ChatGPT command `{play_cmd}` not installed?", file=sys.stderr)
        return 1
    
    voices_path = "/usr/share/piper-voices"
    if not os.path.isdir(voices_path):
        try:
            os.mkdir(voices_path)
        except Exception as e:
            print(f"Voices path `{voices_path}` does not exist, and could not create it. Please create the path and import your voices there.\nmkdir error: `{e}`", file=sys.stderr)
            return 1

    # voice = "en/en_US/ryan/low/en_US-ryan-low.onnx"
    voice = "en/en_GB/alba/medium/en_GB-alba-medium.onnx"


    if not os.path.isfile(voices_path + "/" + voice):
        print(f"voice `{voice}` not found in `{voices_path}`.")
        return 1

    recognizer = sr.Recognizer()
    while not shut_down_requested:
        try:
            prompt, prompt_type = wait_for_voice_prompt(recognizer, KEYWORDS[CURRENT_LANGUAGE])
        except RuntimeError as e:
            print(e)
            continue

        if not prompt:
            continue

        voices_path = "/usr/share/piper-voices"
        subprocess.check_call(f"play {voices_path}/beep.mp3", shell=True)

        cmd = ""
        if prompt_type == PromptType.USER:
            if CURRENT_LANGUAGE in PIPER_LANGS:
                cmd = f"{gpt_cmd} -q \"{prompt}\" | {piper_cmd} --model {voices_path}/{voice} --output_file /tmp/piper_tmp.wav && {play_cmd} /tmp/piper_tmp.wav"
            elif CURRENT_LANGUAGE in GTTS_LANGS:
                cmd = f"{gtts_cmd} -l {GTTS_LANG_FORMAT_MAP[CURRENT_LANGUAGE]} \"$({gpt_cmd} -q \"{prompt}\")\" --output /tmp/gtts_tmp.mp3 && {play_cmd} /tmp/gtts_tmp.mp3"
                print(f"EXECUTING `{cmd}`")
        else:
            cmd = f"echo \"{prompt}\" | {piper_cmd} --model {voices_path}/{voice} --output_file /tmp/piper_tmp.wav && {play_cmd} /tmp/piper_tmp.wav"

        subprocess.Popen(cmd, shell=True)

    return 0


if __name__ == "__main__":
    exit(main(sys.argv))


