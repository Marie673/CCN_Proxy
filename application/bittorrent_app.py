from .bittorrent import BitTorrent


class AlreadyExist(Exception):
    pass


class BitTorrentApp:
    def __init__(self):
        self.file_path = ""
        self.bittorrent_threads = {}

    def register(self, torrent):
        if torrent.info_hash in self.bittorrent_threads:
            raise AlreadyExist('This BitTorrentContent is already registered.')

        bittorrent_thread = BitTorrent(torrent, self.file_path)
        self.bittorrent_threads[torrent.info_hash] = bittorrent_thread
        bittorrent_thread.run()
