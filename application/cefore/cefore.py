import time
import threading
import cefpyco

from .entities import CUBIC
from application.bittorrent import BitTorrent


class Cefore(threading.Thread):
    def __init__(self):
        super().__init__()
        self.cef_handle = cefpyco.CefpycoHandle()

        # About congestion control
        self.RTT = 0.1
        self.cubic = CUBIC()
        self.pending_interests = {} # key: name, data: time of sent interest

        # key: info_hash, data: bittorrent_task_thread
        self.bittorrent_tasks = {}

        # Interestキュー
        self.interest_queue = []

        self.running = True

    def setup(self):
        self.cef_handle.begin()
        self.cef_handle.register("ccnx:/BitTorrent")

    def run(self):
        listen_thread = threading.Thread(target=self.listen)
        listen_thread.start()

        send_thread = threading.Thread(target=self.send_interest)
        send_thread.start()

        try:
            listen_thread.join()
            send_thread.join()
        except KeyboardInterrupt:
            self.running = False
            listen_thread.join()
            send_thread.join()

    def listen(self):
        while self.running:
            start_time = time.time()
            try:
                info = self.cef_handle.receive(timeout_ms=1000)
                if not info.is_succeeded:
                    continue

                if info.is_interest:
                    self.handle_interest(info)

                if info.is_data:
                    self.handle_data(info)

            except Exception as e:
                print(e)
                self.cubic.handle_congestion_event()

        self.cef_handle.end()

    def enqueue_interest(self, name, chunk_num):
        self.interest_queue.append((name, chunk_num))

    def send_interest(self):
        while self.running:
            self.cubic.update()

            for _ in range(int(self.cubic.cwnd)):
                if not self.interest_queue:
                    break
                name, chunk_num = self.interest_queue.pop(0)
                self.cef_handle.send_interest(name, chunk_num=chunk_num)
                self.pending_interests[name] = time.time()

            # タイムアウト検出
            current_time = time.time()
            for name, sent_time in list(self.pending_interests.items()):
                if current_time - sent_time > 2 * self.RTT:
                    self.cubic.handle_congestion_event()
                    del self.pending_interests[name]

            time.sleep(self.RTT)

    def handle_data(self, info):
        name = info.name
        prefix = name.split('/')

        if name in self.pending_interests:
            self.RTT = (self.RTT + (time.time() - self.pending_interests[name])) / 2
            del self.pending_interests[name]

        if prefix[0] == 'ccn:' and prefix[1] == 'BitTorrent':
            info_hash = prefix[2]
            piece_index = int(prefix[3])

            if info_hash in self.bittorrent_tasks:
                bittorrent_instance = self.bittorrent_tasks[info_hash]
                # TODO: 要検証
                bittorrent_instance.receive_piece_data(piece_index, info.payload)

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
            self.handle_interest_bittorrent(info)

    def handle_interest_bittorrent(self, info):
        prefix = info.name.split('/')
        info_hash = prefix[2]
        piece_index = int(prefix[3])

        # info_hashに基づくBitTorrentインスタンスを取得または作成
        if info_hash not in self.bittorrent_tasks:
            self.bittorrent_tasks[info_hash] = BitTorrent()
        bittorrent_instance = self.bittorrent_tasks[info_hash]

        # BitTorrentインスタンスからピースデータを非同期で取得
        piece_data = bittorrent_instance.request_piece(piece_index)

        # CEFでピースデータを送信
        self.cef_handle.send_data(name=info.name, payload=piece_data)
