import os
from flask import Flask, render_template, request, jsonify, g

import psutil


app = Flask(__name__)


@app.route('/')
def index():
    app.logger.debug("get request of index.html")
    return render_template('index.html')


@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    try:
        file.save(os.path.join('/tmp/ccn_proxy/torrent', file.filename))
        return f'{file.filename}がアップロードされました'
    except:
        pass

    try:
        # torrent = Torrent(file)
        # torrent.save()
        # app.logger.info(f"commit torrent info: {torrent.info_hash}")
        pass
    except Exception as e:
        app.logger.error(e)
    return render_template('index.html')


@app.route('/system_info')  # 追加
def system_info():
    cpu_percent = psutil.cpu_percent()
    memory_info = psutil.virtual_memory()
    return jsonify(cpu_percent=cpu_percent, memory_percent=memory_info.percent)


if __name__ == '__main__':
    app.run(debug=True)
