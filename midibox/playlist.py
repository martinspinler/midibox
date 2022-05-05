#!/usr/bin/python3
import json
import asyncio
import aiohttp
import ssl

class PlaylistClient():
    def __init__(self, widget, addr, secure = False, prefix = ''):
        self._prefix = prefix
        self.addr = addr
        #self.w = widget
        self._cb = []
        if widget:
            self._cb.append(widget)
        self._s = "s" if secure else ""
        self._queue = asyncio.Queue()
        self.currentPlaylistId = 8
        self.currentBand = 1

    async def _receive_msg(self, msgid):
        i = 0
        while True:
            i += 1
            if i > 100:
                #print("Keep-alive", time.time())
                await self.ws.send_str("client:keep-alive-hotfix:{}")
                i = 0

            try:
                msg = self._queue.get_nowait()
                if msg == "close":
                    await self._disconnect()
                    return None, None
            except asyncio.QueueEmpty:
                pass
            else:
                await self.ws.send_str("client:" + msg)

            try:
                msg = await self.ws.receive(timeout=0.1)
            except asyncio.TimeoutError as e:
                continue

            if msg.type == aiohttp.WSMsgType.TEXT:
                text = msg.data
                if text.startswith("client:"):
                    _,req, jdata = text.split(":", 2)
                    data = json.JSONDecoder().decode(jdata)
                    if msgid is None or req == msgid:
                        return req, data
                elif text.startswith("lona:"):
                    pass
                else:
                    print(msg)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("Err")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                print("Close")
                #self._reconnect()
                #await self.ws.close()
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("Closed")
                #await self._reconnect()
                await self.session.close()
                await self.connect()

                await self.get_playlist()
            else:
                print(msg.type)
        return None, None

    async def connect(self):
        self.session = aiohttp.ClientSession()
        ssl._create_default_https_context = ssl._create_unverified_context
        self.context = ssl._create_unverified_context()

        self.headers = {}
        resp = await self.session.get(f'http{self._s}://{self.addr}/client/', ssl=self.context, headers=self.headers)
        t1 = await resp.text()
        if 'refresh' in t1:
            resp = await self.session.get(f'http{self._s}://{self.addr}/client/', ssl=self.context, headers=self.headers)
            t1 = await resp.text()
        await self._reconnect()

    async def _reconnect(self):
        self.ws = await self.session.ws_connect(f'ws{self._s}://{self.addr}/client/', ssl=self.context, headers=self.headers)
        msg = f"""lona:[1,null,101,["{self._prefix}/client/",null]]"""

        await self.ws.send_str(msg)

    async def _disconnect(self):
        await self.ws.close()
        await self.session.close()

    def disconnect(self):
        self._queue.put_nowait('close')

    def playlist_item_add(self, si):
        self.send_msg('add', {'songId': si.song['id'], 'playlistId': self.currentPlaylistId})

    def playlist_item_del(self, si):
        self.send_msg('delete', {'id': si, 'playlistId': self.currentPlaylistId})

    def playlist_item_move(self, si, pos):
        self.send_msg('move', {'id': si, 'playlistId': self.currentPlaylistId, 'pos': pos})

    def playlist_item_set(self, id = None, off = None):
        self.send_msg('play', {'id': id, 'playlistId': self.currentPlaylistId, 'off': off})

    def send_msg(self, msg, data = {}):
        self._queue.put_nowait(f'{msg}:' + json.JSONEncoder().encode(data))

    async def send_msg_async(self, msg: str, data = {}):
        await self.ws.send_str(f"client:{msg}:" + json.JSONEncoder().encode(data))

    async def get_messages(self):
        req = True
        while req:
            req, data = await self._receive_msg(None)
            if req in ['add', 'delete', 'update', 'play']:
                for cb in self._cb:
                    cb(req, data)

    async def get_playlist(self):
        await self.send_msg_async("get-playlist", {'playlistId': self.currentPlaylistId})
        _, data = await self._receive_msg('playlist')
        return data

    async def get_db(self):
        await self.send_msg_async("get-active-playlist", {'bandId': self.currentBand})
        _, data = await self._receive_msg('active-playlist')
        self.currentPlaylistId = data['playlistId']

        await self.send_msg_async("get-songlist")
        _, data = await self._receive_msg('songlist')
        j = data
        j = {int(k):v for k,v in j.items()}
        [j[k].update({'id':k}) for k in j.keys()]
        return j

