from flask import Flask, request, render_template, Response
from flask.ext.script import Manager
from tug_simulation import TugSimulation
import json
import re
import threading
import time

app = Flask(__name__)
# manager = Manager(app)

def runSimulation(params):
    sim = TugSimulation(params)
    sim.run()

@app.route('/run_simulation', methods=['GET', 'POST'])
def run_simulation():
    server_ip = request.form.get('server_ip')
    server_port = request.form.get('server_port')
    client_id = request.form.get('client_id')
    socket_id = request.form.get('socket_id')
    run_time_days = request.form.get('run_time_days')
    devices = json.loads(request.form.get('devices'))

    if threading.activeCount() < 7:
        t = threading.Thread(target=runSimulation, args=({
            "server_id": server_ip,
            "server_port": server_port,
            "client_id": client_id,
            "run_time_days": run_time_days,
            "devices": devices,
            "socket_id": socket_id
        },))
        t.start()

        resp = Response(response=json.dumps({"test": 1}), status=200, mimetype="application/json")
    else:
        resp = Response(response="Too many simulations running.", status=500, mimetype="text/html")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    # manager.run(debug=True)
    app.run(debug=True)
