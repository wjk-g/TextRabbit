from flask import Flask, redirect, url_for

from app.redirects import bp
from app.auth.routes import protect_access


@bp.route("/", methods = ["GET"])
@protect_access
def redirect_index():
    return redirect(url_for("nlp.home"), code=301)

@bp.route("/home", methods = ["GET"])
def redirect_home():
    return redirect(url_for("nlp.home"), code=301)

@bp.route("/transcribe", methods = ["GET"])
@protect_access
def redirect_transcribe():
    return redirect(url_for("transcribe.transcribe"), code=301)
