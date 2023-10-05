import asyncio
from .communication_manager import CommunicationManager


class BitTorrent :
    def __init__(self) :
        self.com_mgr = CommunicationManager(self)

    async def start(self) :
        """CommunicationManagerを開始します"""
        await self.com_mgr.run()

    async def request_piece(self, piece_index: int) -> bytes :
        """指定されたインデックスのピースを非同期に要求し、ピースのバイナリデータを返します。"""

        if not self.com_mgr.peers :
            raise Exception("No connected peers to request piece from.")

        # 最初の利用可能なピアからピースを要求します。
        # 複数のピアからの応答を効率的に処理するためのロジックを追加することも考慮されるべきです。
        peer = self.com_mgr.peers[0]
        return await self.com_mgr.request_piece_from_peer(peer, piece_index)
