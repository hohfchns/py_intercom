import logging as log
import time
import socket
import pickle
import select
from typing import Optional
from threading import Thread
from threading import Event as Flag
from helpers.generic.functions import *
from piney_event.event import TypedEvent


class IntercomServer:
    PORT: int = 7091
    BUFSIZE: int = 1024
    LOCALHOST: str = "127.0.0.1"
    MAX_CLIENTS: int = 10

    class Message:
        def __init__(self, data: dict, from_ip: Optional[str] = None, target_ip: Optional[str] = None, kind: Optional[str] = None):
            self.from_ip: Optional[str] = from_ip
            self.target_ip: Optional[str] = target_ip
            self.kind: Optional[str] = kind
            self.data: dict = data

        def __str__(self) -> str:
            from_ip = "UNKOWN"
            if self.from_ip is not None:
                from_ip = self.from_ip
            target_ip = "ALL"
            if self.target_ip is not None:
                target_ip = self.target_ip
            return f"Message from `{from_ip}` to `{target_ip}` | {self.data}"

    received_message_from_server: TypedEvent = TypedEvent(Message)

    @staticmethod
    def test_connection(to_ip: str) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect((to_ip, IntercomServer.PORT))
            s.shutdown(2)
            return True
        except:
            return False

    def __init__(self):
        self._server_thread: Optional[Thread] = None
        self._client_thread: Optional[Thread] = None
        self._clients: list[socket.socket] = []

        self._should_disconnect: Flag = Flag()
        self._should_disconnect.clear()
        self._is_running: Flag = Flag()

        self._send_queue: list[bytes] = []

    def start_server(self) -> str:
        if self._is_running.is_set():
            log.error("Cannot start server as it is open already.")
            return self.LOCALHOST

        self._server_thread = Thread(target=self._server_loop)
        self._server_thread.start()
        self._should_disconnect.clear()
        return self.LOCALHOST

    def _client_handler(self, client: socket.socket, addr) -> None:
        self._clients.append(client)
        log.info(f"Client `{client}` connected")
        try:
            with client:
                while not self._should_disconnect.is_set():
                    data = client.recv(self.BUFSIZE)
                    if data:
                        try:
                            message = pickle.loads(data)
                            message.from_ip = addr[0]
                            log.info(f"Received message from client: `{message}`")
                            if message.target_ip == str(addr[0]):
                                self._send_to_client(client, pickle.dumps(message))
                            else:
                                self._broadcast(pickle.dumps(message))
                        except Exception as e:
                            log.error(f"Got exception while parsing data from client | {e}")
                            continue
        except Exception as e:
            log.error(e)
            self._clients.remove(client)
            return

        self._clients.remove(client)

    def _server_loop(self) -> None:
        self._is_running.set()
        try:
            while self.is_running():
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                    server_socket.setsockopt(
                        socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server_socket.bind(("0.0.0.0", self.PORT))
                    server_socket.listen(self.MAX_CLIENTS)
                    client_socket, address = server_socket.accept()
                    client_thread = Thread(target=self._client_handler, args=[client_socket, address])
                    client_thread.start()
        except Exception as e:
            self._is_running.clear()
            raise e

        self._is_running.clear()

    def _broadcast(self, message: bytes) -> None:
        """Broadcasts a message to all connected clients."""
        for client in self._clients.copy():  # Use copy to avoid modification errors
            self._send_to_client(client, message)

    def _send_to_client(self, client: socket.socket, message: bytes) -> None:
        log.debug(f"Sending message to client `{client}`")
        try:
            client.sendall(message)
        except ConnectionError as e:
            # self._clients.remove(client)  # Remove disconnected client
            log.info(f"Sending to client received ConnectionError | client: {client} | error: {e}")

    def _send_to_client_by_ip(self, ip: str, message: bytes) -> None:
        for c in self._clients:
            if c.getsockname()[0] == ip:
                self._send_to_client(c, message)

    def start_client(self, server_ip: str) -> None:
        if self._is_running.is_set():
            log.error("Cannot start client as it is open already.")
            return

        client_thread = Thread(target=self._client_loop, args=[server_ip])
        client_thread.start()
        self._should_disconnect.clear()

    def _client_loop(self, server_ip: str) -> None:
        self._is_running.set()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client_socket:
                client_socket.connect((server_ip, self.PORT))
                log.info(f"Successfully connected to server at ip `{server_ip}`")
                while not self._should_disconnect.is_set():
                    if self._send_queue:
                        message = self._send_queue.pop(0)
                        client_socket.sendall(message)
                    try:
                        ready = select.select([client_socket], [], [])
                        data = None
                        if ready[0]:
                            data = client_socket.recv(self.BUFSIZE)
                        else:
                            continue

                        try:
                            message = pickle.loads(data)
                            if message.target_ip != "BROADCAST" and message.target_ip not in ip4_addresses():
                                continue

                            log.info(f"Received from server: {message}")
                            IntercomServer.received_message_from_server.emit(message)
                        except Exception as e:
                            log.error(f"Got exception while parsing data from server | {e}")
                            continue
                    except ConnectionError as e:
                        log.error(
                            f"Connection error on client `{client_socket.getsockname()}`: `{e}")
                        break
        except Exception as e:
            self._is_running.clear()
            raise e

        self._is_running.clear()

    def send_data(self, data: dict, target_ip: Optional[str], kind: Optional[str] = None) -> None:
        if not self.is_running():
            log.error("Cannot send data as networking is not running.")
            return

        message = IntercomServer.Message(data, target_ip=target_ip, kind=kind)
        if self.is_server():
            if target_ip and target_ip != "BROADCAST":
                log.debug(f"Server sending message | {message}")
                self._send_to_client_by_ip(target_ip, pickle.dumps(message))
            else:
                log.debug(f"Server sending broadcast message | {message}")
                self._broadcast(pickle.dumps(message))
        else:
            if target_ip == "BROADCAST":
                message.target_ip = "127.0.0.1"

            log.debug(f"Client wants to send data `{data}`")
            self._send_queue.append(pickle.dumps(message))

    def disconnect(self) -> None:
        self._should_disconnect.set()

    def is_running(self) -> bool:
        return self._is_running.is_set()

    def is_server(self) -> bool:
        return True if self.is_running and self._server_thread and self._server_thread.is_alive() else False


if __name__ == "__main__":
    enable_log_to_stdout()

    # server = IntercomServer()
    # server.start_server()
    # time.sleep(1)
    client = IntercomServer()
    # client.start_client(IntercomServer.LOCALHOST)
    client.start_client("192.168.1.17")

    # time.sleep(1)
    # client2 = IntercomServer()
    # client2.start_client(IntercomServer.LOCALHOST)

    # time.sleep(1)
    # client.send_data({"data": ["Hey", "Say"]}, IntercomServer.LOCALHOST)
    # client2.send_data({"data": ["Hey", "Bye"]}, IntercomServer.LOCALHOST)

    # print(IntercomServer.test_connection("192.168.1.102"))
    # while not client._should_disconnect.is_set():
        # pass
