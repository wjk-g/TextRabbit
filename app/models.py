from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, relationship
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import sqlalchemy as sa
import sqlalchemy.orm as so 
from typing import Optional

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    __tablename__ = 'user'
    email: so.Mapped[str] = mapped_column(db.String(100), primary_key=True, unique=True, nullable=False)
    
    # Relationships
    created_transcripts: so.WriteOnlyMapped['Transcript'] = so.relationship(back_populates='created_by')
    created_projects: so.WriteOnlyMapped['Project'] = so.relationship(back_populates='created_by')
    
    # Methods
    def __repr__(self):
        return f'<User: {self.email}>'

class Project(db.Model):
    __tablename__ = 'project'
    name: so.Mapped[str] = so.mapped_column(db.String(100), primary_key=True, nullable=False, unique=True)
    user_email: so.Mapped[str] = so.mapped_column(sa.ForeignKey(User.email), nullable=False, index=True)

    # Relationships
    transcripts: so.WriteOnlyMapped['Transcript'] = so.relationship(back_populates='project')
    created_by: so.Mapped[User] = so.relationship(back_populates='created_projects')

    # Methods
    def __repr__(self):
        return f'<Project: {self.name}>'

# add index=True to datetime columns to be able to easily retrieve data in chronological order
class Transcript(db.Model):
    __tablename__ = 'transcript'
    assemblyai_id: so.Mapped[str] = so.mapped_column(sa.String, primary_key=True, nullable=False, unique=True)
    audio_file_name: so.Mapped[str] = so.mapped_column(sa.String, nullable=False)
    user_email: so.Mapped[str] = so.mapped_column(sa.ForeignKey(User.email), nullable=False, index=True)
    error_message: so.Mapped[Optional[str]] = so.mapped_column(db.String, nullable=True)
    transcription_status: so.Mapped[str] = so.mapped_column(db.String, nullable=False)
    project_name: so.Mapped[str] = so.mapped_column(sa.ForeignKey(Project.name), nullable=False, index=True)
    
    # Relationships
    project: so.Mapped[Project] = so.relationship(back_populates='transcripts')
    created_by: so.Mapped[User] = so.relationship(back_populates='created_transcripts')
    transcript_json: so.Mapped['TranscriptJSON'] = so.relationship(back_populates="transcript_info")

    # Args with default values
    #submitted_on: so.Mapped[datetime] = so.mapped_column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
    created_on: so.Mapped[datetime] = so.mapped_column(db.DateTime, nullable=True, default=lambda: datetime.now(timezone.utc))
    
    # Methods
    def __repr__(self):
        return f'<Transcript: {self.audio_file_name}; Project: {self.project_name}; Status: {self.transcription_status}>'

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
