import threading


class BitTorrent(threading.Thread):
    def __init__(self):
        super().__init__()

    def get_piece(self, piece_index):
        pass
