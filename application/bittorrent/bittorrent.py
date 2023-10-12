import asyncio
import threading

from .entities import Peer, Piece, State
from .communication_manager import CommunicationManager


class BitTorrent(threading.Thread):
    def __init__(self, torrent_metadata, file_path) :
        super().__init__()
        self.torrent_metadata = torrent_metadata
        self.file_path = file_path

        self.pieces = [Piece(index, size, hash_, self.file_path) for index, size, hash_ in self._generate_piece_info()]
        self.peers = []  # 初期化時にはピアはなし

        self.comm_mgr = CommunicationManager(self)

    async def run(self) :
        """CommunicationManagerを開始します"""
        await self.comm_mgr.run()

    async def request_piece(self, piece_index: int) -> bytes :
        """指定されたインデックスのピースを非同期に要求し、ピースのバイナリデータを返します。"""

        if not self.comm_mgr.peers :
            raise Exception("No connected peers to request piece from.")

        # 最初の利用可能なピアからピースを要求します。
        # 複数のピアからの応答を効率的に処理するためのロジックを追加することも考慮されるべきです。
        peer = self.comm_mgr.peers[0]
        return await self.comm_mgr.request_piece_from_peer(peer, piece_index)

    async def request_piece_from_peer(self, peer: Peer, piece_index: int):
        piece = self.pieces[piece_index]
        for block_index in range(piece.number_of_blocks):
            if piece.blocks[block_index].state == State.FREE:
                await peer.request_block(piece_index, block_index)

    async def fetch_piece_data(self, piece_index: int) -> bytes :
        """指定されたピースを取得します。必要に応じてピアから要求を行います。"""
        piece = self.pieces[piece_index]

        # ピースが完了している場合、直接そのデータを返す
        if piece.is_full :
            return await piece.get_data()

        # ピースを持っているピアのリストを取得
        piece_having_peers = [peer for peer in self.peers if peer.bitfield[piece_index]]

        # 一つもピアが該当ピースを持っていない場合、エラーを返す
        if not piece_having_peers :
            raise ValueError(f"No peer has piece {piece_index}")

        # 最初のピアに対してピースのデータを要求
        await self.request_piece_from_peer(piece_having_peers[0], piece_index)

        # ピースが完了するまで待機
        while not piece.is_full :
            await asyncio.sleep(0.5)

        return await piece.get_data()

    async def add_peer(self, peer: Peer):
        """ピアを追加し、CommunicationManagerにそのピアとの通信を開始させます。"""
        self.peers.append(peer)
        await self.comm_manager.add_peer(peer)  # 通信を開始

    async def remove_peer(self, peer: Peer):
        """CommunicationManagerに指示してピアとの通信を終了し、ピアをリストから削除します。"""
        await self.comm_manager.remove_peer(peer)
        self.peers.remove(peer)

    # CommunicationManagerから呼び出される関数
    def handle_received_block(self, piece_index: int, block_offset: int, data: bytes) :
        """CommunicationManagerによって受信されたブロックデータをピースに保存します。"""
        self.pieces[piece_index].set_block(block_offset, data)

    def receive_block_data(self, piece_index: int, block_offset: int, data: bytes) :
        """ピアからのブロックデータを受信し、対応するピースにデータを設定する"""
        piece = self.pieces[piece_index]
        piece.set_block(block_offset, data)

    async def get_piece_data(self, piece_index: int) -> bytes :
        """指定されたピースのデータを取得する。ピースが完了していない場合はエラーを返す。"""
        piece = self.pieces[piece_index]
        return await piece.get_data()

    async def request_specific_piece(self, piece_index: int) :
        """指定されたピースの要求を開始する"""
        piece_having_peers = [peer for peer in self.peers if peer.bitfield[piece_index]]

        # ここでは最初のピアを使用してピースを要求しますが、
        # 最適なピアを選択するロジックも追加できます。
        if piece_having_peers :
            await self.request_piece_from_peer(piece_having_peers[0], piece_index)

    def _generate_piece_info(self):
        piece_hashes = [self.torrent_metadata['pieces'][i:i+20] for i in range(0, len(self.torrent_metadata['pieces']), 20)]
        piece_size = self.torrent_metadata['piece length']
        num_pieces = len(piece_hashes)

        for index in range(num_pieces):
            size = piece_size if index != num_pieces - 1 else self.torrent_metadata['length'] % piece_size
            yield index, size, piece_hashes[index]
