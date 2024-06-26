import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.flaskenv'))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.urandom(24)
    #SQLALCHEMY_DATABASE_URI = 'postgresql://wojtek@localhost:5432/szkutnik'
    #SQLALCHEMY_DATABASE_URI = "sqlite:///szkutnik.db"
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASS')}@"
        f"{os.getenv('DB_HOST')}/{os.getenv('DB_NAME')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    #ADMINS = ['your-email@example.com']
    #LANGUAGES = ['pl', 'en']
    SESSION_TYPE = 'filesystem'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TRANSCRIBE_UPLOAD_FOLDER = os.path.join(basedir, 'app/transcribe/uploads')
    NLP_UPLOAD_FOLDER = os.path.join(basedir, 'app/nlp/uploads')
    MAX_CONTENT_LENGTH = 300 * 1024 * 1024 # max file size = 300MB
    STATIC_FOLDER = os.path.join(basedir, 'app/static')

    # Profiler configuration
    PROFILER_ENABLED = bool(int(os.environ.get('PROFILER_ENABLED', '0')))

    # Redis configuration
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'
