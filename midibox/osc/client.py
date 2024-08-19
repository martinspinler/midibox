import time
import re
import threading
import mido
from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

from typing import Union, Iterable
import socket

import urllib.parse

from ..controller.base import BaseMidibox


class OscClient(threading.Thread):
    def __init__(self, gp, addr):
        threading.Thread.__init__(self)
        self.addr = addr
        self.gp = gp
        self.s = None

    def start(self):
        self.alive = threading.Event()
        self.alive.set()
        threading.Thread.start(self)

    def stop(self):
        self.alive.clear()
        if self.s:
            try:
                self.s.shutdown(socket.SHUT_RDWR)
                self.s.close()
            except OSError:
                pass
        self.join()

    def handle_msg(self, m):
        self.gp.handle_msg(m)

    def send_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value

        for val in values:
            builder.add_arg(val)

        msg = builder.build()
        try:
            self.s.sendall(msg.size.to_bytes(length=4, byteorder='big') + msg._dgram)
        except Exception:
            pass
            raise

    def recv_size(self, size):
        data = b''
        while self.alive.is_set() and len(data) != size:
            try:
                ret = self.s.recv(size - len(data))
                if len(ret) == 0:
                    return None
                data += ret
            except socket.timeout:
                pass
            except ConnectionError:
                pass

        return data if len(data) == size else None

    def connect(self):
        self.s = None
        while self.s is None and self.alive.is_set():
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect(self.addr)
            except OSError:
                self.s = None
                time.sleep(0.1)
        if self.s:
            print("OSC client connected")

    def run(self):
        self.connect()
        while self.alive.is_set():
            data = self.recv_size(4)
            if data is None:
                self.connect()
                continue
            size = int.from_bytes(data, byteorder='big')

            data = self.recv_size(size)
            if data is None:
                self.connect()
                continue

            for m in osc_packet.OscPacket(data).messages:
                self.handle_msg(m)


class OscMidibox(BaseMidibox):
    def __init__(self, url=None, addr="localhost", port=4302, debug=False):
        super().__init__()

        if url:
            addr = urllib.parse.urlsplit(f"//{url}")
            port = addr.port if addr.port else 4302
            connection = addr.hostname, port
        else:
            connection = (addr, port)

        print(f"Using OSC MidiBox client: {connection}")
        self.client = OscClient(self, connection)

        self._pedal_regex = r"pedal(\d+)\.(\w+)"

    def _connect(self):
        self.client.start()

    def _disconnect(self):
        self.client.stop()

    def handle_msg(self, m):
        addr, params = m.message.address, m.message.params
        addr = addr.split("/")

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
                if hasattr(self, f"_{prop}"):
                    setattr(self, f"_{prop}", params[0])
                    kwargs = {prop: getattr(self, prop)}
                    self.emit('control_change', **kwargs)
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
                        grps = match_res.groups()
                        if grps:
                            index = int(grps[0])
                            prop = grps[1]
                            pedal = lr.pedals[index]
                            if hasattr(pedal, prop):
                                kwargs = {prop: getattr(pedal, prop)}
                                setattr(pedal, f"_{prop}", params[0])
                                pedal.emit('control_change', **kwargs)

    def _initialize(self):
        self.client.send_message("/midibox/initialize", None)

    def _write(self, midi):
        self.client.send_message("/midibox/midi", bytes(midi))

    def _write_config(self, name=None, value=None):
        if name:
            self.client.send_message(f"/midibox/{name}", value)
        else:
            print("osc.client._write_config unknown:", name)

    def _write_layer_config(self, lr, name=None, value=None):
        if name:
            self.client.send_message(f"/midibox/layers/{lr._index}/{name}", value)
        else:
            # Initial config: should be fixed in BaseMidibox
            print("Write layer config name empty!")
            pass
