import asyncio
import threading

from .entities import PieceObject
from .communication_manager import CommunicationManager


class BitTorrent(threading.Thread):
    def __init__(self, torrent_metadata, file_path):
        super().__init__()
        self.torrent_metadata = torrent_metadata
        self.file_path = file_path

        self.pieces = [PieceObject(index, size, hash_, self.file_path) for index, size, hash_ in
                       self._generate_piece_info()]

        self.comm_mgr = CommunicationManager(self)

    async def run(self):
        """CommunicationManagerを開始します"""
        await self.comm_mgr.run()

    async def request_piece(self, piece_index: int) -> bytes:
        """指定されたインデックスのピースを非同期に要求し、ピースのバイナリデータを返します。"""

        if not self.comm_mgr.peers:
            raise Exception("No connected peers to request piece from.")

        # 最初の利用可能なピアからピースを要求します。
        # 複数のピアからの応答を効率的に処理するためのロジックを追加することも考慮されるべきです。
        piece = self.pieces[piece_index]
        return await self.comm_mgr.request_piece_from_peer(piece)

    async def request_piece_from_peer(self, piece_index: int):
        piece = self.pieces[piece_index]
        await self.comm_mgr.request_piece_from_peer(piece)

    async def fetch_piece_data(self, piece_index: int) -> bytes:
        """指定されたピースを取得します。必要に応じてピアから要求を行います。"""
        piece = self.pieces[piece_index]

        # ピースが完了している場合、直接そのデータを返す
        if piece.is_full:
            return await piece.get_data()

        # 最初のピアに対してピースのデータを要求
        await self.request_piece_from_peer(piece_index)

        # ピースが完了するまで待機
        while not piece.is_full:
            await asyncio.sleep(0.5)

        return await piece.get_data()

    # CommunicationManagerから呼び出される関数
    def handle_received_block(self, piece_index: int, block_offset: int, data: bytes):
        """CommunicationManagerによって受信されたブロックデータをピースに保存します。"""
        self.pieces[piece_index].set_block(block_offset, data)

    def receive_block_data(self, piece_index: int, block_offset: int, data: bytes):
        """ピアからのブロックデータを受信し、対応するピースにデータを設定する"""
        piece = self.pieces[piece_index]
        piece.set_block(block_offset, data)

    async def get_piece_data(self, piece_index: int) -> bytes:
        """指定されたピースのデータを取得する。ピースが完了していない場合はエラーを返す。"""
        piece = self.pieces[piece_index]
        return await piece.get_data()

    def _generate_piece_info(self):
        piece_hashes = [self.torrent_metadata['pieces'][i:i + 20] for i in
                        range(0, len(self.torrent_metadata['pieces']), 20)]
        piece_size = self.torrent_metadata['piece length']
        num_pieces = len(piece_hashes)

        for index in range(num_pieces):
            size = piece_size if index != num_pieces - 1 else self.torrent_metadata['length'] % piece_size
            yield index, size, piece_hashes[index]
