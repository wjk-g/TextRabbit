import os
from flask import Flask, request, current_app
from flask_session import Session

from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from sqlalchemy.engine import Engine
from sqlalchemy import event

from redis import Redis
from redis.exceptions import ConnectionError

import rq

from config import Config

from werkzeug.middleware.profiler import ProfilerMiddleware

import functools

def get_locale():
    return request.accept_languages.best_match(current_app.config['LANGUAGES'])

db = SQLAlchemy()
migrate = Migrate()

# The create_app function is an application factory
def create_app(config_class=Config):
    
    app = Flask(__name__) # initialize app instance
    app.config.from_object(config_class) # load config from config.py

    db.init_app(app)

    # Enable foreign keys for SQLite | This is not enough to get an SQLite db working correctly
    #@event.listens_for(Engine, "connect")
    #def set_sqlite_pragma(dbapi_connection, connection_record):
    #    cursor = dbapi_connection.cursor()
    #    cursor.execute("PRAGMA foreign_keys=ON")
    #    cursor.close()
    #    print("Foreign keys enabled for SQLite database.")
    
    migrate.init_app(app, db)

    Session(app)

    # The profiler should be enabled before defining the blueprints if we want all the routes to be visible to it
    if app.config['PROFILER_ENABLED']:
        app.wsgi_app = ProfilerMiddleware(app.wsgi_app, restrictions=[30], sort_by=('tottime', 'calls'))

    from app.auth import bp as auth_bp # import auth blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth') # register auth blueprint

    from app.nlp import bp as nlp_bp # import nlp blueprint
    app.register_blueprint(nlp_bp, url_prefix='/nlp') # register nlp blueprint

    from app.transcribe import bp as transcribe_bp # import transcription blueprint
    app.register_blueprint(transcribe_bp, url_prefix='/transcribe') # register transcribe blueprint

    from app.projects import bp as projects_bp # import projects blueprint
    app.register_blueprint(projects_bp, url_prefix='/projects') # register projects blueprint

    from app.redirects import bp as redirects_bp # import auth blueprint
    app.register_blueprint(redirects_bp, url_prefix='') # register auth blueprint

    # Redis and tasks configuration
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('szkutnik-tasks', connection=app.redis)
    # This task will check every hour if there are new transcripts in the cloud
    try:
        app.task_queue.enqueue('app.transcribe.tasks.update_and_download_transcripts', job_timeout=60*60*2) # 2h timeout
        print("Succesfully enqueued the update_and_download_transcripts task.")
    except ConnectionError:
        print("Failed to connect to the Redis server or the server is not running!")

    if not app.debug and not app.testing:
        app.logger.info('Application startup')

    return app

from app import models
