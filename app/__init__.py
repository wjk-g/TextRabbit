import os
from flask import Flask, request, current_app
from flask_session import Session

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from config import Config

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

db = SQLAlchemy()
migrate = Migrate()

# The create_app function is application factory
def create_app(config_class=Config):
    
    app = Flask(__name__) # initialize app instance
    app.config.from_object(config_class) # load config from config.py

    db.init_app(app)
    migrate.init_app(app, db)

    Session(app)

    from app.auth import bp as auth_bp # import auth blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth') # register auth blueprint

    from app.nlp import bp as nlp_bp # import nlp blueprint
    app.register_blueprint(nlp_bp, url_prefix='/nlp') # register nlp blueprint

    from app.transcribe import bp as transcribe_bp # import transcription blueprint
    app.register_blueprint(transcribe_bp, url_prefix='/transcribe') # register transcribe blueprint

    if not app.debug and not app.testing:
        app.logger.info('Microblog startup')

    return app


from app import models
