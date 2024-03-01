from config import Config
import unittest
from app import create_app, db
from app.models import User, Project, Transcript, TranscriptJSON


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    WTF_CSRF_ENABLED = False

