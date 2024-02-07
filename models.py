from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy import JSON 

class Base(DeclarativeBase, MappedAsDataclass):
    pass

db = SQLAlchemy(model_class=Base)

# Association tables
project_users = db.Table(
    'project_users',
    db.Column('project_name', db.ForeignKey('project.name'), primary_key=True),
    db.Column('user_email', db.ForeignKey('user.email'), primary_key=True)
)

project_coordinators = db.Table('project_coordinators',
    db.Column('project_name', db.ForeignKey('project.name'), primary_key=True),
    db.Column('user_email', db.ForeignKey('user.email'), primary_key=True)
)

class Project(db.Model):
    __tablename__ = 'project'
    name: Mapped[str] = mapped_column(db.String(100), primary_key=True, nullable=False)
    description: Mapped[str] = mapped_column(db.Text, nullable=True)
    transcripts: Mapped[list['Transcript']] = relationship('Transcript', backref='project', lazy=True)
    users: Mapped[list['User']] = relationship('User', secondary=project_users, back_populates='projects')
    coordinators: Mapped[list['User']] = relationship('User', secondary=project_coordinators, back_populates='coordinated_projects')

class User(db.Model):
    __tablename__ = 'user'
    email: Mapped[str] = mapped_column(db.String(100), primary_key=True, unique=True, nullable=False)
    projects: Mapped[list['Project']] = relationship('Project', secondary=project_users, back_populates='users')
    coordinated_projects: Mapped[list['Project']] = relationship('Project', secondary=project_coordinators, back_populates='coordinators')

class Transcript(db.Model):
    __tablename__ = 'transcript'
    assemblyai_id: Mapped[str] = mapped_column(db.String, primary_key=True)  # ID assigned by AssemblyAI
    audio_file_name: Mapped[str] = mapped_column(db.String(100), nullable=False)
    project_name: Mapped[str] = mapped_column(db.String, db.ForeignKey('project.name'), nullable=False)
    created_on: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    completed_on: Mapped[datetime] = mapped_column(db.DateTime, nullable=True)
    error_message: Mapped[str] = mapped_column(db.String, nullable=True)
    audio_file_length: Mapped[int] = mapped_column(db.Integer)
    transcription_status: Mapped[str] = mapped_column(db.String, nullable=False)

class TranscriptJSON(db.Model):
    __tablename__ = 'transcript_json'
    transcript_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('transcript.assemblyai_id'), primary_key=True)
    json_content: Mapped[JSON] = mapped_column(db.JSON, nullable=False)
    transcript: Mapped['Transcript'] = relationship('Transcript', backref=db.backref('json_content', uselist=False))

class TranscriptTextFormatted(db.Model):
    __tablename__ = 'transcript_text_formatted'
    transcript_id: Mapped[str] = mapped_column(db.String, db.ForeignKey('transcript.assemblyai_id'), primary_key=True)
    text_processed: Mapped[str] = mapped_column(db.Text, nullable=False)
    transcript: Mapped['Transcript'] = relationship('Transcript', backref=db.backref('text_processed', uselist=False))

# Jsonized transcript processed (coded, tagged, whatever) by OpenAI 
# class ...