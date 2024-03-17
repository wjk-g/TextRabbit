from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone, timedelta
import sqlalchemy as sa
import sqlalchemy.orm as so 
from typing import Optional
from app import db

class Base(DeclarativeBase):
    pass

class User(db.Model):
    __tablename__ = 'user'
    id: so.Mapped[int] = mapped_column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True, index=True)
    name: so.Mapped[str] = mapped_column(db.String(100), nullable=False)
    surname: so.Mapped[str] = mapped_column(db.String(100), nullable=False)
    email: so.Mapped[str] = mapped_column(db.String(100), unique=True, nullable=False)
    
    # Relationships
    created_transcripts: so.WriteOnlyMapped['Transcript'] = so.relationship(back_populates='created_by')
    created_projects: so.WriteOnlyMapped['Project'] = so.relationship(back_populates='created_by')
    
    # Methods
    def __repr__(self):
        return f'<User: {self.email}>'
    
    def get_full_name(self):
        return f'{self.name} {self.surname}'

CET = timezone(timedelta(hours=1))

class Project(db.Model):
    __tablename__ = 'project'
    id: so.Mapped[int] = mapped_column(db.Integer, primary_key=True, autoincrement=True, nullable=False, unique=True, index=True)
    name: so.Mapped[str] = so.mapped_column(db.String(100), nullable=False, unique=True)
    description: so.Mapped[str] = so.mapped_column(db.String(300), nullable=False)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False, index=True)
    date_created: so.Mapped[datetime] = so.mapped_column(db.DateTime, default=lambda: datetime.now(CET))

    
    # Relationships
    transcripts: so.WriteOnlyMapped['Transcript'] = so.relationship(back_populates='project', passive_deletes=True, cascade="all,delete-orphan")
    created_by: so.Mapped[User] = so.relationship(back_populates='created_projects')

    # Methods
    def __repr__(self):
        return f'<Project: {self.name}>'

class Transcript(db.Model):
    __tablename__ = 'transcript'
    assemblyai_id: so.Mapped[str] = so.mapped_column(sa.String, primary_key=True, nullable=False, unique=True)
    audio_file_name: so.Mapped[str] = so.mapped_column(sa.String, nullable=False)
    user_id: so.Mapped[int] = so.mapped_column(sa.ForeignKey(User.id), nullable=False, index=True)
    error_message: so.Mapped[Optional[str]] = so.mapped_column(db.String, nullable=True)
    transcription_status: so.Mapped[str] = so.mapped_column(db.String, nullable=False)
    project_id: so.Mapped[str] = so.mapped_column(sa.ForeignKey(Project.id), nullable=False, index=True)
    
    # Relationships
    project: so.Mapped[Project] = so.relationship(back_populates='transcripts')
    created_by: so.Mapped[User] = so.relationship(back_populates='created_transcripts')
    transcript_json: so.Mapped['TranscriptJSON'] = so.relationship(back_populates="transcript_info", cascade="all,delete")

    # Args with default values
    date_created: so.Mapped[datetime] = so.mapped_column(db.DateTime, default=lambda: datetime.now(CET))
    
    # Methods
    def __repr__(self):
        return f'<Transcript: {self.audio_file_name}; Status: {self.transcription_status}>'

class TranscriptJSON(db.Model):
    __tablename__ = 'transcript_json'
    json_content: so.Mapped[sa.JSON] = so.mapped_column(db.JSON, nullable=False)
    assemblyai_id: so.Mapped[str] = so.mapped_column(db.String, db.ForeignKey('transcript.assemblyai_id'), primary_key=True)
    
    # Relationships
    transcript_info: so.Mapped[Transcript] = so.relationship(back_populates="transcript_json", uselist=False, single_parent=True)
    
    __table_args__ = (sa.UniqueConstraint("assemblyai_id"),)
    
    # Methods
    def __repr__(self):
        return f'<JSON payload of -- {self.transcript_info}>'
