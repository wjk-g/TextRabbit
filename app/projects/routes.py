import os
from sqlalchemy import asc, desc

# Flask imports
from flask import Flask, render_template, session, request, jsonify, redirect, url_for
from sqlalchemy import select

from app.models import User, Project, Transcript
from app.projects.forms import CreateProjectForm, ModifyProjectForm

from app import db
from app.projects import bp
from app.transcribe.transcripts_handler import TranscriptsHandler

from app.auth.routes import protect_access

# Display projects
@bp.route("/projects", methods=["GET"])
@protect_access
def projects():

    projects = Project.query.order_by(desc(Project.date_created)).all()
    
    return render_template(
        "projects/projects.html",
        projects=projects,
    )

# Display projects
@bp.route("/project_transcripts/<int:project_id>", methods=["GET", "POST"])
@protect_access
def project_transcripts(project_id):

    project = Project.query.get(project_id)
    transcripts = Transcript.query.filter(project_id == project_id).order_by(desc(Transcript.date_created)).all()

    # Update the status of transcripts in the db and save the updated transcripts
    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    transcripts_handler.connect_check_update_and_save_transcripts(api_key)
    
    # POST requests only
    if request.method == "POST":
        transcript_id = transcripts_handler.get_transcript_id_from_multiple_forms()
        return transcripts_handler.write_transcript_to_file(transcript_id)

    return render_template(
        "projects/project_transcripts.html",
        project=project,
        transcripts=transcripts,
        transcripts_being_processed=transcripts_handler.transcripts_being_processed,
    )

# Create project
@bp.route("/create_project", methods=["GET", "POST"])
@protect_access
def create_project():

    form = CreateProjectForm()

    if form.validate_on_submit():

        project = Project(
            name=form.name.data,
            description=form.description.data,
            user_id=session["user_id"]
        )
        db.session.add(project)
        db.session.commit()
        return redirect(url_for("projects.projects"))

    return render_template(
        "projects/create_project.html",
        create_project_form=form,
    )

# Modify project
@bp.route("/edit_project/<int:project_id>", methods=["GET", "POST"])
@protect_access
def edit_project(project_id):

    project = Project.query.get(project_id)
    form = ModifyProjectForm(obj=project)

    if form.validate_on_submit():
        form.populate_obj(project)
        db.session.commit()
        return redirect(url_for("projects.projects"))

    return render_template(
        "projects/edit_project.html",
        edit_project_form=form,
    )
