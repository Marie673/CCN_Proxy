import asyncio
from typing import Tuple


# ... [他のインポート]

class PeerConnection :
    def __init__(self, ip: str, port: int, piece_manager) :
        self.ip = ip
        self.port = port
        self.piece_manager = piece_manager  # Pieceのクラスインスタンス
        self.reader: asyncio.StreamReader = None
        self.writer: asyncio.StreamWriter = None

    async def connect(self) :
        self.reader, self.writer = await asyncio.open_connection(self.ip, self.port)
        # ここでBitTorrentのハンドシェイクを行います。

    async def request_piece(self, piece_index: int) -> bool :
        """特定のpieceを要求して、それをダウンロードします。

        成功した場合はTrueを、失敗した場合はFalseを返します。
        """
        block_info = self.piece_manager.get_empty_block(piece_index)
        if not block_info :
            return False

        piece_idx, block_offset, block_length = block_info
        # ここでBitTorrentのメッセージを使用してブロックを要求します。

        # ブロックのデータを読み取ります。
        block_data = await self._read_block(block_length)
        if not block_data :
            return False

        self.piece_manager.set_block(piece_index, block_offset, block_data)
        if self.piece_manager.are_all_blocks_full(piece_index) :
            success = self.piece_manager.set_to_full(piece_index)
            if success :
                await self.piece_manager.write_on_disk(piece_index)
                return True
        return False

    async def _read_block(self, length: int) -> bytes :
        """指定された長さのデータを非同期に読み取ります。"""
        try :
            data = await self.reader.readexactly(length)
            return data
        except asyncio.IncompleteReadError :
            return b''

    async def close(self) :
        if self.writer :
            self.writer.close()
            await self.writer.wait_closed()
