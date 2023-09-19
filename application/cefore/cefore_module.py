import threading
import cefpyco

from application.bittorrent import BitTorrent


class CcnNListener(threading.Thread):
    def __init__(self):
        super().__init__()
        self.cef_handle = cefpyco.CefpycoHandle()

        # key: info_hash, data: bittorrent_task_thread
        self.bittorrent_tasks = {}

    def setup(self):
        self.cef_handle.begin()
        self.cef_handle.register("ccnx:/BitTorrent")

    def start(self):
        while True:
            info = self.cef_handle.receive()
            if info.is_succeeded and info.is_interest:
                self.handle_interest(info)

    def handle_interest(self, info):
        prefix = info.name.split('/')
        """
        prefix[0] = ccnx:
        prefix[1] = BitTorrent
        prefix[2] = info_hash
        prefix[3] = piece_index
        """

        # logger.debug(prefix)
        if prefix[0] != "ccnx:":
            return

        if prefix[1] == 'BitTorrent':
            self.handle_bittorrent(info)

    def handle_bittorrent(self, info):
        name = info.name.split('/')
        info_hash = name[2]
        piece_index = int(name[3])

        chunk_num = info.chunk_num
        end_chunk_num = info.end_chunk_num

        if self.bittorrent_tasks not in info_hash:
            # torrent_file =
            bittorrent_task = BitTorrent()
            self.bittorrent_tasks[info_hash] = bittorrent_task
        else:
            bittorrent_task = self.bittorrent_tasks[info_hash]

        data = bittorrent_task.get_piece(piece_index)


