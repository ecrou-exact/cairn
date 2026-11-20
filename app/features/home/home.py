from flask import Blueprint, jsonify, render_template

from app.core.utils.decorators import public
from app.features.home import home_core

home = Blueprint("home", __name__)
health = Blueprint("health", __name__)


@home.route("/")
def index():
    return render_template("home/index.html", activity=home_core.recent_activity())


@health.route("/health")
@public
def health_check():
    return jsonify(status="ok")
