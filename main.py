from firebase_functions import https_fn
from firebase_admin import initialize_app
import flask

initialize_app()
app = flask.Flask(__name__)

@app.route("/")
def hello():
    return "Hello from Firebase!"

@https_fn.on_request()
def api(req: https_fn.Request) -> https_fn.Response:
    with app.request_context(req.environ):
        return app.full_dispatch_request()
