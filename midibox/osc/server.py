import time
import socket
import socketserver
import threading

import netifaces

from zeroconf import ServiceInfo, Zeroconf

from typing import Any, Tuple, Optional

from pythonosc.osc_message_builder import OscMessageBuilder
from pythonosc.osc_message import OscMessage
from pythonosc.osc_bundle import OscBundle
from pythonosc.osc_packet import OscPacket

from .osc import OscValue

DispatchedOscCb = Any


class TCPOSCRequestHandler(socketserver.BaseRequestHandler):
    server: "TCPOSCServer"

    def setup(self) -> None:
        super().setup()
        print("TCP OSC client connected", self.client_address)
        self.server.clients.append(self)

    def _recv(self, size: int) -> bytes:
        recv = bytes()
        while len(recv) != size:
            if self.request is None:
                raise ConnectionError
            b = self.request.recv(size - len(recv))
            if not b:
                raise ConnectionError

            recv += b
        return recv

    def handle(self) -> None:
        try:
            while True:
                data = self._recv(4)
                size = int.from_bytes(data, byteorder='big')
                data = self._recv(size)
                for m in OscPacket(data).messages:
                    self.handle_message(m.message.address, *m.message.params)
        except ConnectionError:
            pass

    def finish(self) -> None:
        print("TCP OSC client disconnected", self.client_address)
        self.server.clients.remove(self)
        super().finish()

    def handle_message(self, address: str, *params: *Tuple[OscValue, ...]) -> None:
        pass

    def send_message(self, address: str, *values: *Tuple[OscValue, ...]) -> None:
        builder = OscMessageBuilder(address=address)
        for val in values:
            builder.add_arg(val)
        msg = builder.build()
        self.send_msg(msg)

    def send_msg(self, msg: OscMessage | OscBundle) -> None:
        try:
            self.request.sendall(msg.size.to_bytes(length=4, byteorder='big') + msg.dgram)
        except Exception:
            pass


class DispatchedOSCRequestHandler(TCPOSCRequestHandler):
    # TODO: Fix Any, see callback below
    def map(self, path: str, callback: DispatchedOscCb, *args: *Tuple[Any, ...]) -> None:
        self._dispatcher_maps[path] = (callback, args)

    def setup(self) -> None:
        super().setup()
        self._dispatcher_maps: dict[str, Tuple[DispatchedOscCb, Tuple[Any]]] = {}

    def handle_message(self, address: str, *values: *Tuple[OscValue, ...]) -> None:
        mapping = self._dispatcher_maps.get(address)
        if mapping:
            callback, args = mapping
            callback(address, *args, *values)


class TCPOSCServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    clients: list[TCPOSCRequestHandler]
    _server_thread: Optional[threading.Thread]

    def __init__(self, server_address: Tuple[str, int], RequestHandlerClass: type[DispatchedOSCRequestHandler]) -> None:
        self._server_thread = None
        super().__init__(server_address, RequestHandlerClass)

    def server_activate(self) -> None:
        self.clients = []
        super().server_activate()

    def shutdown(self) -> None:
        for c in self.clients:
            try:
                c.request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            finally:
                c.request.close()
        super().shutdown()

    def start(self) -> None:
        if self._server_thread is not None:
            raise RuntimeError
        self._server_thread = threading.Thread(target=self.serve_forever)
        self._server_thread.start()

    def stop(self) -> None:
        if self._server_thread is None:
            raise RuntimeError
        self.shutdown()
        self._server_thread.join()


def getIPv4Addresses() -> dict[str, str]:
    ret = {}
    for i in netifaces.interfaces():
        if i == 'lo':
            continue
        try:
            ret[i] = netifaces.ifaddresses(i)[netifaces.AF_INET][0]['addr']
        except KeyError:
            pass
    return ret


class ZCPublisher(threading.Thread):
    def __init__(self, port: int = 4302, oscname: str = "MidiboxOSC", allowed_ips: list[str] | None = None):
        self._stop_event = threading.Event()
        self._zc_svcs: dict[str, tuple[Zeroconf, ServiceInfo]] = {}
        super().__init__(target=self._run, args=(port, oscname, allowed_ips))
        self.start()

    def stop(self):
        self._stop_event.set()
        self.join()

    def _run(self, port, oscname, allowed_ips):
        zc_service = "_osc._tcp.local."
        zc_name = oscname + "." + zc_service

        while not self._stop_event.is_set():
            # Workaround to publish all IP addresses
            for ifname, ip in getIPv4Addresses().items():
                zc_name = f"{oscname}_{ifname}_{port}.{zc_service}"
                if ip in self._zc_svcs or (allowed_ips is not None and ip not in allowed_ips):
                    continue
                si = ServiceInfo(zc_service, zc_name, port, addresses=[ip]) # type: ignore[list-item]
                zc = Zeroconf([ip])
                zc.register_service(si)
                print("Zeroconf register %s on IP %s" % (zc_name, ip))
                self._zc_svcs.update({ip: (zc, si)})
            time.sleep(1)

        for ip, (zc, si) in self._zc_svcs.items():
            zc.close()
