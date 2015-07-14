from flask import Flask, request, render_template, Response
from flask.ext.script import Manager 
import tests.grid_controller
import tests.generator_and_light
import tests.generator_and_fan
import json
import re

app = Flask(__name__)
manager = Manager(app)

# @app.route('/api/tests')
# def tests():
#     print(dir())
#     resp = Response(json.dumps([fname for fname in dir() if re.match('test_', fname)]), status=200, mimetype="application/json")
#     resp.headers['Access-Control-Allow-Origin'] = '*'
#     return resp

@app.route('/api/test_grid_controller')
def test_grid_controller():
    resp = Response(response=json.dumps(tests.grid_controller.run()), status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/test_generator_and_light')
def test_generator_and_light():
    resp = Response(response=json.dumps(tests.generator_and_light.run()), status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

@app.route('/api/test_generator_and_fan')
def test_generator_and_fan():
    results_json = tests.generator_and_fan.run(output_json=True)
    resp = Response(response=json.dumps(results_json), status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    return resp

if __name__ == '__main__':
    manager.run()
