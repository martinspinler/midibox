import socket
import urllib.parse
import time
import re
import threading
import mido

from typing import Tuple, Optional

from pythonosc.osc_packet import OscPacket, TimedMessage
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY

from .osc import OscValue
from ..controller.base import BaseMidibox, PropChange, General, Layer, Pedal


class OscClient(threading.Thread):
    def __init__(self, gp: "OscMidibox", addr: Tuple[str, int]):
        threading.Thread.__init__(self)
        self.addr = addr
        self.gp = gp
        self.s: Optional[socket.socket] = None

    def start(self) -> None:
        self.alive = threading.Event()
        self.alive.set()
        threading.Thread.start(self)

    def stop(self) -> None:
        self.alive.clear()
        if self.s:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()
            except OSError:
                pass
        self.join()

    def handle_msg(self, m: TimedMessage) -> None:
        self.gp.handle_msg(m)

    def send_message(self, address: str, *values: *Tuple[OscValue, ...]) -> None:
        builder = OscMessageBuilder(address=address)

        for val in values:
            builder.add_arg(val)

        self.send_msg(builder.build())

    def send_msg(self, msg: OscMessage | OscBundle) -> None:
        if self.s is None:
            raise ConnectionError
        self.s.sendall(msg.size.to_bytes(length=4, byteorder='big') + msg.dgram)

    def _recv(self, size: int) -> bytes:
        recv = bytes()
        while len(recv) != size:
            if self.s is None:
                raise ConnectionError
            b = self.s.recv(size - len(recv))
            if not b:
                raise ConnectionError
            recv += b

        return recv

    def connect(self) -> None:
        self.s = None
        while self.s is None and self.alive.is_set():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect(self.addr)
                self.s = s
            except OSError:
                time.sleep(0.1)
        if self.s:
            print("OSC client connected")

    def run(self) -> None:
        self.connect()
        while self.alive.is_set():
            try:
                data = self._recv(4)
                size = int.from_bytes(data, byteorder='big')
                data = self._recv(size)

                for m in OscPacket(data).messages:
                    self.handle_msg(m)
            except ConnectionError:
                self.connect()


class OscMidibox(BaseMidibox):
    def __init__(self, url: Optional[str] = None, addr: str = "localhost", port: int = 4302, debug: bool = False) -> None:
        super().__init__()

        if url is not None:
            paddr = urllib.parse.urlsplit(f"//{url}")
            port = paddr.port if paddr.port else 4302
            if paddr.hostname is None:
                raise ValueError
            connection = (paddr.hostname, port)
        else:
            connection = (addr, port)

        print(f"Using OSC MidiBox client: {connection}")
        self.client = OscClient(self, connection)

        self._pedal_regex = r"pedal(\d+)\.(\w+)"

    def connect(self) -> None:
        self.client.start()

    def disconnect(self) -> None:
        self.client.stop()

    def handle_msg(self, m: TimedMessage) -> None:
        addrs, params = m.message.address, m.message.params
        addr = addrs.split("/")

        if len(addr) < 2 or addr[1] != "midibox":
            return

        addr = addr[2:]

        if addr == ["midi"]:
            lmsg = list(params[0])
            msg = mido.Message.from_bytes(lmsg)
            for cb in self._callbacks:
                cb(msg)
            return

        if len(addr) >= 1:
            prop = addr[0]
            addr = addr[1:]
            if len(addr) == 0:
                if hasattr(self.general, f"_{prop}"):
                    setattr(self.general, f"_{prop}", params[0])
                    kwargs = {prop: getattr(self.general, prop)}
                    self.general.emit('control_change', **kwargs)
            elif prop == "layers" and len(addr) >= 2:
                lr = self.layers[int(addr[0])]
                prop = addr[1]
                addr = addr[2:]
                if len(addr) == 0:
                    if hasattr(lr, f"_{prop}"):
                        setattr(lr, f"_{prop}", params[0])
                        kwargs = {prop: getattr(lr, prop)}
                        lr.emit('control_change', **kwargs)
                    else:
                        match_res = re.fullmatch(self._pedal_regex, prop)
                        if match_res is None:
                            grps = None
                        else:
                            grps = match_res.groups()

                        if grps is not None:
                            index = int(grps[0])
                            prop = grps[1]
                            pedal = lr.pedals[index]
                            if hasattr(pedal, prop):
                                kwargs = {prop: getattr(pedal, prop)}
                                setattr(pedal, f"_{prop}", params[0])
                                pedal.emit('control_change', **kwargs)

    def initialize(self) -> None:
        self.client.send_message("/midibox/initialize")

    def set_props(self, props: list[PropChange]) -> None:
        bundle = OscBundleBuilder(IMMEDIATELY)
        for p in props:
            address = "/midibox/"
            if isinstance(p.source, General):
                address += f"{p.name}"
            elif isinstance(p.source, Layer):
                address += f"layers/{p.source._index}/{p.name}"
            elif isinstance(p.source, Pedal):
                address += f"layers/{p.source._layer._index}/pedal{p.source._index}.{p.name}"

            builder = OscMessageBuilder(address=address)
            builder.add_arg(p.value)
            bundle.add_content(builder.build()) # type: ignore

        msg = bundle.build()
        self.client.send_msg(msg)

    def sendmsg(self, msg: mido.Message) -> None:
        self.client.send_message("/midibox/midi", bytes(msg.bytes()))
