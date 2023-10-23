import logging
from struct import unpack, pack
import random
import socket
import bitstring

HANDSHAKE_PROTOCOL = b'BitTorrent protocol'
HANDSHAKE_PROTOCOL_LEN = len(HANDSHAKE_PROTOCOL)
LENGTH_PREFIX = 4


class WrongMessageException(Exception):
    pass


class MessageDispatcher:
    def __init__(self, payload: bytes):
        self.payload = payload

    def dispatch(self) -> 'Message':
        payload_length, message_id = unpack('>IB', self.payload[:5])

        map_id_to_message = {
            0: Choke,
            1: UnChoke,
            2: Interested,
            3: NotInterested,
            4: Have,
            5: BitField,
            6: Request,
            7: Piece,
            8: Cancel,
            9: Port
        }

        if message_id not in map_id_to_message:
            raise WrongMessageException('Wrong message id')

        return map_id_to_message[message_id].from_bytes(self.payload)

class Message:
    def to_bytes(self) -> bytes:
        raise NotImplementedError()

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Message':
        raise NotImplementedError()

    @staticmethod
    def _pack(format_string: str, *args) -> bytes:
        return pack(format_string, *args)

    @staticmethod
    def _unpack(format_string: str, data: bytes) -> tuple:
        return unpack(format_string, data)


class UdpTrackerConnection(Message):
    def __init__(self):
        super().__init__()
        self.conn_id = pack('>Q', 0x41727101980)
        self.action = pack('>I', 0)
        self.trans_id = pack('>I', random.randint(0, 100000))

    def to_bytes(self) -> bytes:
        return self.conn_id + self.action + self.trans_id

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'UdpTrackerConnection':
        obj = cls()
        obj.action, = unpack('>I', payload[:4])
        obj.trans_id, = unpack('>I', payload[4:8])
        obj.conn_id, = unpack('>Q', payload[8:])
        return obj


class UdpTrackerAnnounce(Message):
    def __init__(self, info_hash: bytes, conn_id: bytes, peer_id: bytes):
        super().__init__()
        self.peer_id = peer_id
        self.conn_id = conn_id
        self.info_hash = info_hash
        self.trans_id = pack('>I', random.randint(0, 100000))
        self.action = pack('>I', 1)

    def to_bytes(self) -> bytes:
        conn_id = pack('>Q', self.conn_id)
        downloaded = pack('>Q', 0)
        left = pack('>Q', 0)
        uploaded = pack('>Q', 0)
        event = pack('>I', 0)
        ip = pack('>I', 0)
        key = pack('>I', 0)
        num_want = pack('>i', -1)
        port = pack('>h', 8000)

        msg = (conn_id + self.action + self.trans_id + self.info_hash + self.peer_id + downloaded +
               left + uploaded + event + ip + key + num_want + port)
        return msg


class UdpTrackerAnnounceOutput:
    def __init__(self):
        self.action = None
        self.transaction_id = None
        self.interval = None
        self.leechers = None
        self.seeders = None
        self.list_sock_addr = []

    def from_bytes(self, payload):
        self.action, = unpack('>I', payload[:4])
        self.transaction_id, = unpack('>I', payload[4:8])
        self.interval, = unpack('>I', payload[8:12])
        self.leechers, = unpack('>I', payload[12:16])
        self.seeders, = unpack('>I', payload[16:20])
        self.list_sock_addr = self._parse_sock_addr(payload[20:])

    @staticmethod
    def _parse_sock_addr(raw_bytes):
        socks_addr = []

        for i in range(int(len(raw_bytes) / 6)):
            start = i * 6
            end = start + 6
            ip = socket.inet_ntoa(raw_bytes[start:(end - 2)])
            raw_port = raw_bytes[(end - 2):end]
            port = raw_port[1] + raw_port[0] * 256

            socks_addr.append((ip, port))

        return socks_addr


class Handshake(Message):
    payload_length = 68
    total_length = payload_length

    def __init__(self, info_hash: bytes, peer_id: bytes = b''):
        super(Handshake).__init__()
        assert len(info_hash) == 20
        assert len(peer_id) < 255
        self.peer_id = peer_id
        self.info_hash = info_hash

    def to_bytes(self) -> bytes:
        reserved = b'\x00' * 8
        handshake = pack(">B{}s8s20s20s".format(HANDSHAKE_PROTOCOL_LEN),
                         HANDSHAKE_PROTOCOL_LEN,
                         HANDSHAKE_PROTOCOL,
                         reserved,
                         self.info_hash,
                         self.peer_id)
        logging.debug(f"{self.peer_id}, {self.info_hash}, {handshake}")
        return handshake

    @classmethod
    def from_bytes(cls, payload: bytes) -> 'Handshake':
        pstrlen, = unpack(">B", payload[:1])
        pstr, reserved, info_hash, peer_id = unpack(">{}s8s20s20s".format(pstrlen), payload[1:cls.total_length])
        if pstr != HANDSHAKE_PROTOCOL:
            raise ValueError("Invalid protocol")
        return cls(info_hash, peer_id)


class KeepAlive(Message):
    payload_length = 0
    total_length = 4

    def to_bytes(self) -> bytes:
        return self._pack(">I", self.payload_length)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, = cls._unpack(">I", payload[:cls.total_length])
        if payload_length != 0:
            raise WrongMessageException("Not a keep alive message")
        return KeepAlive()


class Choke(Message):
    message_id = 0
    chokes_me = True
    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return self._pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id = cls._unpack(">IB", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a choke message")
        return Choke()


class UnChoke(Message):
    message_id = 1
    chokes_me = False
    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return self._pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id = cls._unpack(">IB", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not an UnChoke message")
        return UnChoke()


class Interested(Message):
    message_id = 2
    interested = True
    payload_length = 1
    total_length = 4 + payload_length

    def to_bytes(self) -> bytes:
        return self._pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id = cls._unpack(">IB", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not an interested message")
        return Interested()


class NotInterested(Message):
    message_id = 3
    interested = False
    payload_length = 1
    total_length = 5

    def to_bytes(self) -> bytes:
        return self._pack(">IB", self.payload_length, self.message_id)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id = cls._unpack(">IB", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a Non Interested message")
        return NotInterested()


class Have(Message):
    message_id = 4
    payload_length = 5
    total_length = 4 + payload_length

    def __init__(self, piece_index: int):
        self.piece_index = piece_index

    def to_bytes(self) -> bytes:
        return self._pack(">IBI", self.payload_length, self.message_id, self.piece_index)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id, piece_index = cls._unpack(">IBI", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a Have message")
        return Have(piece_index)


class BitField(Message):
    message_id = 5
    payload_length = -1  # This will be determined later based on the bitfield
    total_length = -1  # This will be determined later based on the payload_length

    def __init__(self, bitfield: 'bitstring.BitArray'):
        self.bitfield = bitfield
        self.bitfield_as_bytes = bitfield.tobytes()
        self.bitfield_length = len(self.bitfield_as_bytes)
        self.payload_length = 1 + self.bitfield_length
        self.total_length = 4 + self.payload_length

    def to_bytes(self) -> bytes:
        return self._pack(">IB{}s".format(self.bitfield_length), self.payload_length, self.message_id, self.bitfield_as_bytes)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id = cls._unpack(">IB", payload[:5])
        bitfield_length = payload_length - 1
        raw_bitfield, = cls._unpack(">{}s".format(bitfield_length), payload[5:5 + bitfield_length])
        bitfield = bitstring.BitArray(bytes=bytes(raw_bitfield))
        return BitField(bitfield)


class Request(Message):
    message_id = 6
    payload_length = 13
    total_length = 4 + payload_length

    def __init__(self, piece_index: int, block_offset: int, block_length: int):
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def to_bytes(self) -> bytes:
        return self._pack(">IBIII", self.payload_length, self.message_id, self.piece_index, self.block_offset, self.block_length)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id, piece_index, block_offset, block_length = cls._unpack(">IBIII", payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a Request message")
        return Request(piece_index, block_offset, block_length)


class Piece(Message):
    message_id = 7
    payload_length = -1  # This will be determined later based on the block_length
    total_length = -1  # This will be determined later based on the payload_length

    def __init__(self, block_length: int, piece_index: int, block_offset: int, block: bytes):
        self.block_length = block_length
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block = block
        self.payload_length = 9 + block_length
        self.total_length = 4 + self.payload_length

    def to_bytes(self) -> bytes:
        return self._pack(">IBII{}s".format(self.block_length), self.payload_length, self.message_id, self.piece_index, self.block_offset, self.block)

    @classmethod
    def from_bytes(cls, payload: bytes):
        block_length = len(payload) - 13
        payload_length, message_id, piece_index, block_offset, block = cls._unpack(">IBII{}s".format(block_length), payload[:13 + block_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a Piece message")
        return Piece(block_length, piece_index, block_offset, block)


class Cancel(Message):
    message_id = 8
    payload_length = 13
    total_length = 4 + payload_length

    def __init__(self, piece_index: int, block_offset: int, block_length: int):
        super(Cancel, self).__init__()
        self.piece_index = piece_index
        self.block_offset = block_offset
        self.block_length = block_length

    def to_bytes(self) -> bytes:
        return self._pack(">IBIII",
                    self.payload_length,
                    self.message_id,
                    self.piece_index,
                    self.block_offset,
                    self.block_length)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id, piece_index, block_offset, block_length = cls._unpack(">IBIII",
                                                                                     payload[:cls.total_length])
        if message_id != cls.message_id:
            raise WrongMessageException("Not a Cancel message")

        return Cancel(piece_index, block_offset, block_length)


class Port(Message):
    message_id = 9
    payload_length = 5
    total_length = 4 + payload_length

    def __init__(self, listen_port: int):
        super(Port, self).__init__()
        self.listen_port = listen_port

    def to_bytes(self) -> bytes:
        return self._pack(">IBI",
                    self.payload_length,
                    self.message_id,
                    self.listen_port)

    @classmethod
    def from_bytes(cls, payload: bytes):
        payload_length, message_id, listen_port = cls._unpack(">IBI", payload[:cls.total_length])

        if message_id != cls.message_id:
            raise WrongMessageException("Not a Port message")

        return Port(listen_port)
