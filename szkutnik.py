import sqlalchemy as sa
import sqlalchemy.orm as so
from app import create_app, db
from app.models import (
    User,
    Project,
    Transcript,
    TranscriptJSON,
)

app = create_app()

with app.app_context():
    db.create_all()

@app.shell_context_processor
def make_shell_context():
    return {'sa': sa, 'so': so, 'db': db, 'User': User, 'Project': Project,
            'Transcript': Transcript, 'TranscriptJSON': TranscriptJSON}