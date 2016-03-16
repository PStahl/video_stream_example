#!/usr/bin/env python
#
# Project: Video Streaming with Flask
# Author: Log0 <im [dot] ckieric [at] gmail [dot] com>
# Date: 2014/12/21
# Website: http://www.chioka.in/
# Description:
# Modified to support streaming out with webcams, and not just raw JPEGs.
# Most of the code credits to Miguel Grinberg, except that I made a small tweak. Thanks!
# Credits: http://blog.miguelgrinberg.com/post/video-streaming-with-flask
#
# Usage:
# 1. Install Python dependencies: cv2, flask. (wish that pip install works like a charm)
# 2. Run "python main.py".
# 3. Navigate the browser to the local webpage.
import requests
import socket
import json
import time

from flask import Flask, render_template, Response, request
from camera import VideoCamera

app = Flask(__name__)
log = app.logger


@app.route('/')
def index():
    return render_template('form.html')


@app.route('/submit', methods=['POST'])
def submit():
    return render_template('index.html', url=request.form['url'],
                           filename=request.form['filename'])


def gen(url, filename):
    remote_address = url.split(":")[0]
    remote_port = int(url.split(":")[1])

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #host = "10.3.63.255"
    host = "localhost"
    port = 8090

    s.bind((host, port))
    s.listen(1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
    data = json.dumps({
        "filename": filename,
        "url": "{}:{}".format(host, port)
    })

    log.info("Sending request to {}:{}".format(remote_address, remote_port))
    sock.sendto(data, (remote_address, remote_port))

    log.info("Listeneing on {}:{}".format(host, port))

    last_shown = -1
    last_showed = None
    receivers = set()
    while True:
        conn, addr = s.accept()
        message = []
        while True:
            d = conn.recv(1024)
            if not d:
                break
            else:
                message.append(d)
        if not message:
            continue

        data = json.loads(''.join(message))
        receivers.add(data['id'])
        if data and data['frame_count'] == -1:
            log.info("Closing connection. Received from: {}".format(receivers))
            s.close()
            return
        elif data and data['frame_count'] > last_shown:
            if not data['frame_count'] == last_shown + 1:
                print "\n\n"
                print last_shown, data['frame_count']
            log.debug("Received frame {} from {}: total receivers: {}".format(
                data['frame_count'], data['id'], len(receivers)))

            FPS = 30
            while last_showed and last_showed + (1.0 / FPS) > time.time():
                print "{}, {}, {}".format(last_showed, last_showed + (1.0 / FPS), time.time())
                print "sleep"
                time.sleep(0.05)
            last_showed = time.time()
            #last_showed + (1.0 / FPS) if last_showed else time.time()
            last_shown = data['frame_count']
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + data['frame'].encode("latin-1") + b'\r\n\r\n')


@app.route('/run_get')
def run_get():
    url = "http://localhost:8089"
    r = requests.get(url, stream=True)

    return '\n'.join(list(r.iter_lines()))


@app.route('/video_feed/<url>/<filename>')
def video_feed(url, filename):
    return Response(gen(url, filename),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=8080)
