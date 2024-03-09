import yaml
import json
import plac
import sys
import subprocess
from plac import opt
import logging as log

from py_intercom.intercom import Intercom
from py_intercom.command.command_manager import CommandManager

from piney_event.event import TypedEvent
from piney_event.event import Event

class CommandsInterface():
    set_language_requested: TypedEvent = TypedEvent(str)
    shut_off: Event = Event()

    @staticmethod
    def set_language(command_conf: dict, to: str) -> str:
        CommandsInterface.set_language_requested.emit(to)
        return command_conf["message"]

    @staticmethod
    def turn_off(command_conf: dict) -> str:
        CommandsInterface.shut_off.emit()
        return command_conf["message"]

    @staticmethod
    def shut_down_computer(command_conf: dict) -> str:
        subprocess.Popen("sleep 2 && systemctl poweroff", shell=True) 
        return command_conf["message"]


class App:
    @staticmethod
    def _enable_log_to_stdout():
        root = log.getLogger()
        root.setLevel(log.DEBUG)

        handler = log.StreamHandler(sys.stdout)
        handler.setLevel(log.DEBUG)
        formatter = log.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        root.addHandler(handler)


    def on_command_requested(self, command_id: str, language: str, command_map: dict) -> None:
        command = command_map[language][command_id]
        callback_id = command["callback"]
        if not callback_id.startswith("CommandsInterface."):
            return

        cb = getattr(CommandsInterface, callback_id.split(".")[1])
        if not cb:
            return

        args = command["args"] if "args" in command else []
        kwargs = command["kwargs"] if "kwargs" in command else {}
        
        ret = cb(command, *args, **kwargs)
        if ret:
            log.info(f"Command {command_id} returned prompt '{ret}'")
            CommandManager.say = ret


    @opt("config_file", abbrev="C")
    @opt("commands_file", abbrev="c")
    def main(self, config_file: str = "config.yml", commands_file: str = "commands.json") -> int:
        App._enable_log_to_stdout()
        config = {}
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        if config == {}:
            log.error(f"Could not read config file at `{config_file}`")
            return -1

        command_map = {}
        with open(commands_file, "r") as f:
            command_map = json.load(f)
        if command_map == {}:
            log.error(f"Could not read commands file at `{config_file}`")
            return -1

        intercom = Intercom(config, command_map)

        CommandManager.callback_requested.connect(self.on_command_requested)
        CommandsInterface.set_language_requested.connect(intercom.set_language)
        CommandsInterface.shut_off.connect(intercom.stop_main_loop)

        intercom.start_main_loop()
        while intercom.main_loop and intercom.main_loop.is_alive():
            try:
                pass
            except KeyboardInterrupt:
                intercom.stop_main_loop()
                break

        return intercom.get_exit_code()

if __name__ == "__main__":
    app = App()
    plac.call(app.main)


