from flask import Blueprint

bp = Blueprint('redirects', __name__)

from app.redirects import routes
