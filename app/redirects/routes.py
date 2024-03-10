from flask import Flask, redirect, url_for, render_template

from app.redirects import bp
from app.auth.routes import protect_access

@bp.route("/", methods = ["GET"])
@protect_access
def welcome():
    return render_template("welcome.html")

@bp.route("/home", methods = ["GET"])
def redirect_home():
    return redirect(url_for("nlp.home"), code=301)

@bp.route("/transcribe", methods = ["GET"])
def redirect_transcribe():
    return redirect(url_for("transcribe.transcribe"), code=301)
