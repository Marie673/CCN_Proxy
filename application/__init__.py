from flask import Flask

app = Flask(__name__)

# bittorrentとceforeモジュールをインポート
from application.bittorrent import bittorrent_module
from application.cefore import cefore_module
