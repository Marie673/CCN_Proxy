from flask import Flask
from flask_sqlalchemy import SQLAlchemy

# bittorrentとceforeモジュールをインポート
from application.bittorrent import bittorrent_module
from application.cefore import cefore_module

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///torrent.db'
db = SQLAlchemy(app)
