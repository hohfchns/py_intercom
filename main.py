import yaml
import json
import plac
import subprocess
import time
from helpers.generic.functions import *
from typing import Optional
from shutil import which
from typing import Callable
from plac import opt
import logging as log
from threading import Thread

from py_intercom.intercom import Intercom
from py_intercom.command.command_manager import CommandManager

from piney_event.event import TypedEvent
from piney_event.event import Event

class CommandsInterface():
    set_language_requested: TypedEvent = TypedEvent(str)
    shut_off: Event = Event()

    @staticmethod
    def shut_down(command_conf: dict) -> str:
        subprocess.Popen("sleep 2 && poweroff", shell=True)
        return command_conf["message"]

    @staticmethod
    def set_language(command_conf: dict, to: str) -> str:
        CommandsInterface.set_language_requested.emit(to)
        return command_conf["message"]

    @staticmethod
    def turn_off(command_conf: dict) -> str:
        CommandsInterface.shut_off.emit()
        return command_conf["message"]

class App:
    def start(self) -> None:
        """
        Will start the app, parsing commands from cli, setting up the main loop, etc.
        """
        plac.call(self._main)

    def __init__(self) -> None:
        self.intercom: Optional[Intercom] = None
        self.commands_extension: Optional[type | object] = None

    def set_extension(self, handler: type | object) -> None:
        """
        :param handler: Commands starting with the `CommandsExtension` callback will be forwarded to `handler`, ideally provide as `type` (class name) for static method usage, or as `object` for member funtion usage.
        """
        self.commands_extension = handler

    def _on_command_requested(self, command_id: str, language: str, command_map: dict) -> None:
        command = command_map[language][command_id]
        callback_id = command["callback"]
        if not callback_id.startswith("CommandsInterface.") and not callback_id.startswith("CommandsExtension."):
            return

        _ci, func = callback_id.split(".")
        cb = None
        try:
            cb = getattr(CommandsInterface, func)
        except:
            if not self.commands_extension:
                return

            try:
                cb = getattr(self.commands_extension, func)
            except:
                return

        args = command["args"] if "args" in command else []
        kwargs = command["kwargs"] if "kwargs" in command else {}
        
        ret = cb(command, *args, **kwargs)
        if ret:
            log.info(f"Command {command_id} returned prompt '{ret}'")
            CommandManager.say = ret

    @staticmethod
    def deferred_call(method: Callable, time_defer_secs: float, args: list = [], kwargs: dict = {}) -> None:
        t = Thread(target=App._deferred_call_thread, args=[method, time_defer_secs, args, kwargs])
        t.start()

    @staticmethod
    def _deferred_call_thread(method: Callable, time_defer_secs: float, args: list = [], kwargs: dict = {}) -> None:
        time.sleep(time_defer_secs)
        method(*args, **kwargs)

    def _on_set_language_requested(self, language: str) -> None:
        if not self.intercom:
            return

        self.deferred_call(self.intercom.set_language, 1.0, [language])

    @opt("config_file", abbrev="C")
    @opt("commands_file", abbrev="c")
    def _main(self, config_file: str = "config.yml", commands_file: str = "commands.json") -> int:
        config = {}
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)
        if config == {}:
            print(f"Could not read config file at `{config_file}`", file=sys.stderr)
            return -1

        if "log_level" in config:
            enable_log_to_stdout(config["log_level"])
        else:
            enable_log_to_stdout()

        command_map = {}
        with open(commands_file, "r") as f:
            command_map = json.load(f)
        if command_map == {}:
            log.error(f"Could not read commands file at `{config_file}`")
            return -1

        self.intercom = Intercom(config, command_map)

        self.intercom.command_requested.connect(self._on_command_requested)
        CommandsInterface.set_language_requested.connect(self._on_set_language_requested)
        CommandsInterface.shut_off.connect(self.intercom.stop_main_loop)

        self.intercom.start_main_loop()
        while self.intercom._main_loop and self.intercom._main_loop.is_alive():
            try:
                pass
            except KeyboardInterrupt:
                self.intercom.stop_main_loop()
                break

        return self.intercom.get_exit_code()

if __name__ == "__main__":
    app = App()
    app.start()


