from flask import Blueprint

bp = Blueprint('transcribe', __name__)

from app.transcribe import routes
