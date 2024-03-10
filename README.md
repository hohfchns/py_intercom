# PyIntercom


# Requirements

This project is currently only tested on Linux, however it might run in other OS's ¯\\_(ツ)_/¯ 

# Setup

for chatgpt, set the `OPENAI_API_KEY` environment variable, for example:
``` bash
export OPENAI_API_KEY="sk-the-rest-of-the-key"
```
You can find or create your key at [the OpenAI website](`https://platform.openai.com/api-keys`)

The project expects your desired microphone to be the default one.

## Create a new virtual environent
### Conda method (recommended)

``` bash
conda env create -f environent.yml
```

Run the project:
``` bash
conda activate py-intercom
python main.py
```

### Pip + venv method
``` bash
env_name=".venv"
python -m venv $env_name
source $env_name/bin/activate # Will have to be run one every new shell
```

Install the python dependencies:
``` bash
$env_name/bin/pip install -r requirments.txt
```

Run the project:
``` bash
$env_name/bin/python main.py
```

# Usage

A simple autorun script could be written like the following:
``` bash
#!/bin/bash
cd py_intercom_dir
export OPENAI_API_KEY="sk-the-rest-of-the-key"
# In the case conda does not recognize the activate command, uncomment the below line
# eval "$(conda shell.bash hook)"
conda activate py-intercom
python main.py
```

After completing the [setup](#requirements), you can run the program.

The program will only respond when you call it by it's name (default - Intercom / "אינטרקום")

The program has a few commands that will call their own code, anything else will be sent directly to ChatGPT

The program can take as arguments a config file, and commands index, by default located in the project as `config.yml` and `commands.json`

``` bash
python main.py -c my_config_file.yml -C my_commands_index.json
```


