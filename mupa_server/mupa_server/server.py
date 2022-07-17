from __future__ import annotations

import base64
import dataclasses
from threading import Lock
from typing import Optional, Protocol, Type, Union
import socketserver
import contextlib

import sounddevice
import numpy as np

_DTYPE = "int32"
_ENCODING = "utf-8"


class SignalInput(Protocol):
    def get_window(self, samples: int) -> np.array:
        ...

    def get_sample_rate(self) -> float:
        ...

    def get_max_samples(self) -> float:
        ...

    def __enter__(self) -> SignalInput:
        ...

    def __exit__(self, *args) -> None:
        ...


@dataclasses.dataclass
class AudioInput:
    _max_window_seconds: float = 3
    _device: Optional[Union[int, str]] = None
    _channels: list[int] = dataclasses.field(default_factory=lambda: [1])
    _sample_rate: int = -1

    def __post_init__(self) -> None:
        if self._sample_rate == -1:
            device_info = sounddevice.query_devices(self._device, "input")
            self._sample_rate = device_info["default_samplerate"]

        self._max_samples = int(self._max_window_seconds * self._sample_rate)
        self._data = np.zeros(self._max_samples, dtype=_DTYPE)
        self._data_lock = Lock()

        self._channel_indexes = [c - 1 for c in self._channels]
        self._stream = sounddevice.InputStream(
            device=self._device,
            channels=max(self._channels),
            samplerate=self._sample_rate,
            callback=self.audio_callback,
            dtype=_DTYPE,
        )

    def audio_callback(self, indata: np.array, *_):
        """This is called (from a separate thread) for each audio block."""

        # take the mean of all selected channels
        data = np.mean(indata[:, self._channel_indexes], axis=1)
        shift = len(data)

        with self._data_lock:
            self._data = np.roll(self._data, -shift, axis=0)
            self._data[-shift:] = data

    def get_window(self, samples: int) -> np.array:
        with self._data_lock:
            return self._data[-samples:]

    def get_sample_rate(self) -> int:
        return self._sample_rate

    def get_max_samples(self) -> int:
        return self._max_samples

    def __enter__(self) -> AudioInput:
        self._stream.__enter__()
        return self

    def __exit__(self, *args) -> None:
        return self._stream.__exit__(*args)


@contextlib.contextmanager
def tcp_handler(input_: SignalInput) -> Type[socketserver.BaseRequestHandler]:
    class Handler(socketserver.StreamRequestHandler):
        def handle(self) -> None:
            while True:
                data = self.rfile.readline().decode(_ENCODING).strip()
                if data == "sr":
                    self.request.sendall(f"{input_.get_sample_rate()}\n".encode(_ENCODING))
                    continue
                if data == "ms":
                    self.request.sendall(f"{input_.get_max_samples()}\n".encode(_ENCODING))
                    continue
                if data == "q":
                    return
                try:
                    sample_count = int(data)
                except ValueError:
                    pass
                else:
                    if sample_count > input_.get_max_samples():
                        self.request.sendall("err:max_samples_exceeded\n".encode(_ENCODING))
                        continue
                    samples = input_.get_window(sample_count)
                    data = base64.b64encode(samples.tobytes())
                    self.request.sendall(data + b"\n")
                    continue
                self.request.sendall("err:invalid_command\n".encode(_ENCODING))

    with input_:
        yield Handler


@contextlib.contextmanager
def make_server(input_: SignalInput, port: int, host: str="localhost") -> socketserver.TCPServer:
    with tcp_handler(input_) as handler, socketserver.TCPServer((host, port), handler) as server:
        yield server
