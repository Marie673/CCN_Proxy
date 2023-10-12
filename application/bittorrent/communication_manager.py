import asyncio
import logging

from .entities.peer import Peer
from .entities.peer.message import Message, Handshake, KeepAlive, Choke, UnChoke, Interested, NotInterested, Have, BitField, Request, Piece, Cancel, Port


logger = logging.getLogger(__init__)


class CommunicationManager:
    def __init__(self, bittorrent):
        self.bittorrent = bittorrent
        self.peers: list[Peer] = []

    async def run(self):
        """すべてのピアとの通信を監視し続けます"""
        while True:
            await self.listener()
            await asyncio.sleep(1)

    async def listener(self):
        """ピアからのメッセージを非同期に処理します"""

        # イテレート中の変更時にエラーを回避するためにcopy()
        for peer in self.peers.copy():
            try:
                payload = await peer.reader.read(4096)
                if not payload:
                    continue

                peer.read_buffer += payload

                for msg in peer.get_messages():
                    await self._process_new_message(msg, peer)

            except Exception as e:
                await self.remove_peer(peer)

    async def request_piece_from_peer(self, peer: Peer, piece_index: int) -> bytes:
        """指定されたピアから指定されたインデックスのピースを非同期に要求し、ピースのバイナリデータを返します。"""
        return await peer.fetch_piece(piece_index)

    async def add_peer(self, peer: Peer):
        """ピアをリストに追加します"""
        self.peers.append(peer)

    async def remove_peer(self, peer: Peer):
        """指定されたピアとの通信を終了し、ピアをリストから削除します"""
        await peer.close()
        self.peers.remove(peer)

    async def remove_unhealthy_peer(self):
        for peer in self.peers.copy():
            if peer.healthy is False:
                await self.remove_peer(peer)

    def has_unchocked_peers(self):
        for peer in self.peers.copy():
            if peer.is_unchoked():
                return True
        return False

    async def _process_new_message(self, new_message: Message, peer: Peer) :
        """受信したメッセージを非同期に処理します"""

        if isinstance(new_message, Handshake) or isinstance(new_message, KeepAlive) :
            logger.error("Handshake or KeepALive should have already been handled")

        elif isinstance(new_message, Choke) :
            logger.debug("Choke")
            await peer.handle_choke()

        elif isinstance(new_message, UnChoke) :
            logger.debug("UnChoke")
            await peer.handle_unchoke()

        elif isinstance(new_message, Interested) :
            logger.debug("Interested")
            await peer.handle_interested()

        elif isinstance(new_message, NotInterested) :
            logger.debug("NotInterested")
            await peer.handle_not_interested()

        elif isinstance(new_message, Have) :
            # logger.debug("Have")
            await peer.handle_have(new_message)

        elif isinstance(new_message, BitField) :
            logger.debug("BitField")
            await peer.handle_bitfield(new_message)

        elif isinstance(new_message, Request) :
            logger.debug("Request")
            await peer.handle_request(new_message)

        if isinstance(new_message, Piece):
            piece_index = new_message.piece_index
            block_offset = new_message.block_offset
            data = new_message.block
            self.bittorrent.handle_received_block(piece_index, block_offset, data)


        elif isinstance(new_message, Cancel) :
            logger.debug("Cancel")
            await peer.handle_cancel()

        elif isinstance(new_message, Port) :
            logger.debug("Port")
            await peer.handle_port_request()

        else :
            logger.error("Unknown message")
