from flask import Blueprint, jsonify, render_template

from app.core.utils.decorators import public
from app.core.utils.events import latest_event_id
from app.features.home import home_core
from app.features.tasks import workflow

home = Blueprint("home", __name__)
health = Blueprint("health", __name__)


@home.route("/")
def index():
    after = latest_event_id()
    return render_template("home/index.html", **home_core.today(), types=workflow.types(), events_after=after)


@health.route("/health")
@public
def health_check():
    return jsonify(status="ok")
