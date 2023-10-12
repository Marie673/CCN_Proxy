from typing import Optional
import asyncio
import bitstring
import struct
import time

from .message import Handshake, KeepAlive, Interested, MessageDispatcher, WrongMessageException, UnChoke

peer_id = "test"


class Peer:
    """
    BitTorrentのピアを表現するクラス。各ピアとの通信やデータの交換を管理します。
    """
    def __init__(self, info_hash: bytes, number_of_pieces: int, ip: str, port: int):
        self.ip = ip
        self.port = port
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

        self.info_hash = info_hash
        self.bit_field = bitstring.BitArray(number_of_pieces)

        self.last_call = time.time()
        self.healthy = False
        self.state = {
            'am_choking' : True,
            'am_interested' : False,
            'peer_choking' : True,
            'peer_interested' : False,
        }

        self.read_buffer = b''

    def __hash__(self):
        return '{}:{}:{}'.format(self.info_hash, self.ip, self.port)

    async def connect(self):
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        await self.do_handshake()

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    def is_eligible(self):
        now = time.time()
        return (now - self.last_call) > 0  # 0.001

    def _send_to_peer(self, msg):
        self.writer.write(msg)

    async def do_handshake(self):
        handshake = Handshake(self.info_hash, peer_id=bytes(peer_id, 'utf-8'))
        self._send_to_peer(handshake.to_bytes())

    async def _read_block(self, length: int) -> bytes:
        try:
            return await asyncio.wait_for(self.reader.readexactly(length), timeout=5)
        except (asyncio.IncompleteReadError, asyncio.CancelledError, ConnectionResetError, asyncio.TimeoutError):
            return b''

    async def request_piece(self, piece_index: int, block_info: tuple, on_piece_received: callable) -> bool:
        if not block_info:
            return False

        piece_idx, block_offset, block_length = block_info
        await self.send_interested()

        block_data = await self._read_block(block_length)
        if not block_data:
            return False

        success = on_piece_received(piece_index, block_offset, block_data)
        return success

    async def send_interested(self):
        msg = Interested().to_bytes()
        self.writer.write(msg)
        await self.writer.drain()

    async def get_messages(self) :
        while len(self.read_buffer) > 4 and self.healthy :
            if (not self.has_handshacked and self._handle_handshake()) or self._handle_keep_alive() :
                continue

            payload_length, = struct.unpack(">I", self.read_buffer[:4])
            total_length = payload_length + 4

            if len(self.read_buffer) < total_length :
                break
            else :
                payload = self.read_buffer[:total_length]
                self.read_buffer = self.read_buffer[total_length :]

            try :
                received_message = MessageDispatcher(payload).dispatch()
                if received_message :
                    yield received_message
            except WrongMessageException as e :
                pass

    def has_piece(self, index):
        return self.bit_field[index]

    def am_choking(self):
        return self.state['am_choking']

    def am_unchoking(self):
        return not self.am_choking()

    def is_choking(self) :
        return self.state['peer_choking']

    def is_unchoked(self) :
        return not self.is_choking()

    def is_interested(self) :
        return self.state['peer_interested']

    def am_interested(self) :
        return self.state['am_interested']

    def _handle_handshake(self) :
        try :
            handshake_message = Handshake.from_bytes(self.read_buffer)
            self.has_handshacked = True
            self.read_buffer = self.read_buffer[handshake_message.total_length :]
            return True
        except Exception :
            self.healthy = False

        return False

    def _handle_keep_alive(self):
        try:
            keep_alive = KeepAlive.from_bytes(self.read_buffer)
        except WrongMessageException:
            return False
        """
        except Exception:
            logger.exception("Error KeepALive, (need at least 4 bytes : {})".format(len(self.read_buffer)))
            return False
        """

        self.read_buffer = self.read_buffer[KeepAlive.total_length:]
        return True

    async def handle_choke(self):
        self.state['peer_choking'] = True

    async def handle_unchoke(self):
        self.state['peer_choking'] = False

    async def handle_interested(self) :
        self.state['peer_interested'] = True
        if self.am_choking():
            unchoke = UnChoke().to_bytes()
            self._send_to_peer(unchoke)

    async def handle_not_interested(self) :
        self.state['peer_interested'] = False

    async def handle_have(self, have) :
        """
        :type have: message.Have
        """
        self.bit_field[have.piece_index] = True

        if self.is_choking() and not self.state['am_interested']:
            interested = Interested().to_bytes()
            self._send_to_peer(interested)
            self.state['am_interested'] = True

    async def handle_bitfield(self, bitfield) :
        """
        :type bitfield: message.BitField
        """
        self.bit_field = bitfield.bitfield

        if self.is_choking() and not self.state['am_interested']:
            interested = Interested().to_bytes()
            self._send_to_peer(interested)
            self.state['am_interested'] = True

    # TODO: 未実装
    async def handle_request(self, request) :
        """
        :type request: message.Request
        """
        if self.is_interested() and self.is_unchoked():
            return request

    @staticmethod
    async def handle_piece(message) :
        piece = (message.piece_index, message.block_offset, message.block)
        return piece

    # TODO: 未実装
    async def handle_cancel(self):
        pass

    # TODO: 未実装
    async def handle_port_request(self):
        pass

