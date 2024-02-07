# PyIntercom


## Requirements

This project is currently Linux exclusive, however it might run in WSL ¯\\_(ツ)_/¯ 

### Packages:
- `piper` - For Text To Speech
- `play` - For playing sounds (`sox` package)
- `chatgpt` - For ChatGPT integration; [get here](https://github.com/kardolus/chatgpt-cli)

***You must have all packages above in your PATH***

### Other

Currently the TTS voice is hardcoded to the path `/usr/share/piper-voices/en/en_US/ryan/low/en_US-ryan-low.onnx`

Currently you must have a sound effect file at `/usr/share/piper-voices/beep.mp3`

### Setup

for chatgpt, set the `OPENAI_API_KEY` environment variable, for example:
``` bash
export OPENAI_API_KEY="sk-the-rest-of-the-key"
```
You can find or create your key at [the OpenAI website](`https://platform.openai.com/api-keys`)

The project expects your desired microphone to be the default one.

Create a new virtual environent:
``` bash
env_name=".venv"
python -m venv $env_name
source $env_name/bin/activate # Will have to be run one every new shell
```

Install the python dependencies:
``` bash
$env_name/bin/pip install SpeechRecognition PyAudio gtts
```

Run the project:
``` bash
$env_name/bin/python main.py
```

## Usage

After completing the [setup](#requirements), you can run the program.

The program will only respond when you call it by it's name (default - Intercom / "אינטרקום")

The program has a few commands that will call their own code, anything else will be sent directly to ChatGPT

The commands can be viewed in the `COMMANDS` constant in `main.py`

