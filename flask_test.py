from flask import Flask, request, render_template, Response
from flask.ext.script import Manager 
import tests.grid_controller
import tests.generator_and_light
import json

app = Flask(__name__)
manager = Manager(app)

@app.route('/api/grid_controller')
def grid_controller():
    resp = Response(response=json.dumps(tests.grid_controller.run()), status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/generator_and_light')
def generator_and_light():
    resp = Response(response=json.dumps(tests.generator_and_light.run()), status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    manager.run()
