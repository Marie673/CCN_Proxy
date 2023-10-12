import math
from typing import List
import hashlib
import time
import asyncio
import aiofiles

from .block import Block, BLOCK_SIZE, State

PENDING_TIME = 5


class Piece(object):
    def __init__(self, piece_index: int, piece_size: int, piece_hash: str, file_path):
        self.state = State.FREE

        self.piece_index = piece_index
        self.piece_size = piece_size
        self.piece_hash = piece_hash

        self.is_full: bool = False
        # pieceが保管されているディレクトリのパス
        self.file_path = file_path + '/' + str(piece_index)

        self.number_of_blocks: int = int(math.ceil(float(piece_size) / BLOCK_SIZE))

        self.blocks: List[Block] = [Block() for _ in range(self.number_of_blocks)]
        if self.piece_size % BLOCK_SIZE != 0:
            self.blocks[-1].block_size = self.piece_size % BLOCK_SIZE

    def reset(self):
        """ピースの状態を初期化します"""
        self.is_full = False
        for block in self.blocks:
            block.state = State.FREE
            block.data = b''

    def is_complete(self) -> bool:
        """すべてのブロックが完全であるかどうかを確認します"""
        return all(block.state == State.FULL for block in self.blocks)

    def get_missing_block(self) -> int:
        """まだ受信していない最初のブロックのインデックスを返します"""
        for index, block in enumerate(self.blocks):
            if block.state == State.FREE:
                return index
        return -1  # すべてのブロックが存在する場合

    def update_block_status(self):  # if block is pending for too long : set it free
        for i, block in enumerate(self.blocks):
            if block.state == State.PENDING and (time.time() - block.last_seen) > PENDING_TIME:
                self.blocks[i] = Block()

    def set_block(self, offset: int, data: bytes):
        """指定されたオフセットに対応するインデックスのブロックにデータを設定します"""
        block_index = int(offset / BLOCK_SIZE)
        if self.blocks[block_index].state != State.FULL:
            self.blocks[block_index].data = data
            self.blocks[block_index].state = State.FULL
            if self.is_complete():
                asyncio.create_task(self._validate_and_save())

    async def get_data(self) -> bytes :
        """ピースの完全なバイナリデータを返します。Lazy Loadingを使用。"""
        if not self.is_full:
            raise ValueError("Piece is not complete.")

        offset = self.piece_index * self.piece_size
        async with aiofiles.open(self.file_path, "rb") as file:
            await file.seek(offset)
            return await file.read(self.piece_size)

    def _validate_piece(self) -> bool:
        """ピースが完全であり、ハッシュが一致するかどうかを確認します"""
        concatenated_data = b''.join([block.data for block in self.blocks])
        if hashlib.sha1(concatenated_data).digest() == self.piece_hash:
            self.is_full = True
            return True
        self.reset()  # ピースのハッシュが一致しない場合はリセットします
        return False

    async def _validate_and_save(self):
        """ピースが完了したら、ハッシュを検証して、ディスクに保存します"""
        if self._validate_piece():
            await self._write_to_disk()
            for block in self.blocks:
                block.data = b''  # メモリを解放するためにデータをクリア

    async def _write_to_disk(self):
        """ピースのデータを指定されたファイルパスに保存します。"""
        if not self.is_full :
            raise ValueError("Piece is not complete.")

        async with aiofiles.open(self.file_path, "r+b") as file :
            offset = self.piece_index * self.piece_size
            file.seek(offset)
            file.write(self.get_data())
