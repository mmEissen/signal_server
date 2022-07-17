import socket

import base64
import numpy as np


_DTYPE = "int32"
_ENCODING = "utf-8"


class Client:
    _BUFFSIZE = 4096

    def __init__(self, host: str="localhost", port: int=5032) -> None:
        self._host = host
        self._port = port
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._max_samples = -1
        self._sample_rate = -1
        self._next_message_part = b""

    def _send(self, command: str) -> None:
        self._socket.sendall(f"{command}\n".encode(_ENCODING))

    def _read_line(self) -> bytes:
        message = self._next_message_part
        while True:
            data = self._socket.recv(self._BUFFSIZE)
            parts = data.split(b"\n")
            message += parts[0]
            if len(parts) == 2:
                self._next_message_part = parts[1]
                return message

    def _request(self, command: str) -> bytes:
        self._send(command)
        return self._read_line()

    def connect(self) -> None:
        self._socket.connect((self._host, self._port))
        response = self._request("ms")
        self._max_samples = int(response.decode(_ENCODING))
        response = self._request("sr")
        self._sample_rate = float(response.decode(_ENCODING))
    
    def close(self) -> None:
        self._socket.shutdown()
        self._socket.close()

    def __enter__(self) -> None:
        self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def get_window(self, samples: int) -> np.array:
        window_data = self._request(str(samples))
        return np.frombuffer(base64.b64decode(window_data), dtype=_DTYPE)

    def get_max_samples(self) -> int:
        return self._max_samples

    def get_sample_rate(self) -> float:
        return self._sample_rate
