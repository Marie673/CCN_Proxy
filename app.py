import os
import sqlite3

from flask import Flask, render_template, request, jsonify, g
from flask_sqlalchemy import SQLAlchemy

from application.cefore import cefore_module
import psutil

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///torrent.db'
db = SQLAlchemy(app)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file.save(os.path.join("uploads", file.filename))
    return "File uploaded"


@app.route('/system_info')  # 追加
def system_info():
    cpu_percent = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    return jsonify(cpu_percent=cpu_percent, memory_percent=memory_info.percent)


if __name__ == '__main__':
    app.run(debug=True)
