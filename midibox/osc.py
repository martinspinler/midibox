import threading
from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

from typing import List, Tuple, Union, Any, Iterable
import socket

from base import BaseMidiBox


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

#    def start_listen(self):
        #t = threading.Thread(target = self.listen)
        #t.start()

    def stop(self):
        self.alive.clear()
        if self.s:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        self.join()

    def handle_msg(self, m):
        print(m.message.address, m.message.params)
        self.gp.handle_msg(m)
        #if m.message.address == "/next":
        #    self.gp.playlist.gp.document.next_page()
        #if m.message.address == "/prev":
        #    self.gp.playlist.gp.document.prev_page()

    def send_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value
        for val in values: builder.add_arg(val)
        msg = builder.build()
        #try:
        if True:
            self.s.sendall(msg.size.to_bytes(length=4, byteorder='little') + msg._dgram)
        #except:
        #    pass

    def run(self):
        while self.s == None and self.alive.is_set():
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect(self.addr)
            except OSError:
                self.s = None
                time.sleep(1)

        if self.s:
            print("OSC client connected")

        while self.alive.is_set():
            try:
                sz = self.s.recv(4)
                if not sz:
                    break
                data = self.s.recv(int.from_bytes(sz, byteorder='little'))
                for m in osc_packet.OscPacket(data).messages:
                    self.handle_msg(m)
            except socket.timeout:
                pass


class OscMidibox(BaseMidiBox):
    def __init__(self):
        self.client = OscClient(self, ("midibox", 4300))
        self.client.start()

        print("Using OSC MidiBox client")
        super().__init__()

        #self.portin.callback = self.inputCallback

    def _write(self, msg):
        print([hex(x) for x in msg])
        #self.portout.send(mido.Message.from_bytes(msg))
        self.client.send_message(f"/midibox/midi/send", msg)

    def _write_layer(self, l, cmd):
        layer = self.layers[l]
        #print(cmd)
        if 'active' in cmd:
            self.client.send_message(f"/midibox/layer/{l}/active", layer._active and not self._mute)
        if 'transposition' in cmd:
            self.client.send_message(f"/midibox/layer/{l}/transposition", layer._transposition + 0x40 + layer._transposition_extra)

        if 'rangel' in cmd:
            self.client.send_message(f"/midibox/layer/{l}/rangel", layer._rangel)
        if 'rangeu' in cmd:
            self.client.send_message(f"/midibox/layer/{l}/rangeu", layer._rangeu)

    def _read_layer(self, layer, length = 8):
        return []
