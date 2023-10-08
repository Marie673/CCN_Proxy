import asyncio
from .entities.peer import Peer
from application.bittorrent.entities.peer.message import Message, Handshake, KeepAlive, Choke, UnChoke, Interested, NotInterested, Have, BitField, Request, Piece, Cancel, Port
from logger import logger  # 必要に応じて正しいパスを指定してください

class CommunicationManager:
    def __init__(self, bittorrent):
        self.bittorrent = bittorrent
        self.peers: list[Peer] = []

    async def run(self):
        """すべてのピアとの通信を監視し続けます"""
        while True:
            await self.listener()

    async def listener(self):
        """ピアからのメッセージを非同期に処理します"""
        for peer in self.peers:
            if not peer.healthy:
                self.remove_peer(peer)
            try:
                payload = await self._read_from_socket(peer.socket)
                peer.read_buffer += payload

                for msg in peer.get_messages():
                    await self._process_new_message(msg, peer)

            except Exception as e:
                self.remove_peer(peer)
                logger.error(e)

    async def request_piece_from_peer(self, peer: Peer, piece_index: int) -> bytes:
        """指定されたピアから指定されたインデックスのピースを非同期に要求し、ピースのバイナリデータを返します。"""
        return await peer.fetch_piece(piece_index)

    def remove_peer(self, peer):
        """指定されたピアをピアリストから削除します"""
        if peer in self.peers:
            try:
                peer.socket.close()
            except Exception:
                pass
            self.peers.remove(peer)

    async def _read_from_socket(self, sock) -> bytes:
        """ソケットからデータを非同期に読み取ります"""
        data = b''
        try:
            data = await asyncio.get_event_loop().sock_recv(sock, 4096)
        except Exception:
            logger.exception("Recv failed")
        return data

    async def _process_new_message(self, new_message: Message, peer: Peer):
        """受信したメッセージを非同期に処理します"""
        # ... [以前の回答と同様のメッセージ処理ロジック]

