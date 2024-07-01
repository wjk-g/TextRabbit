import os

import assemblyai as aai

# Flask imports
from flask import Flask, render_template, session, request, jsonify, redirect, url_for

# Load forms
from app.transcribe.forms import TranscribeForm

# Load classes
from app.transcribe.transcripts_handler import TranscriptsHandler

from app.transcribe import bp

from app.models import Project, User, Transcript, TranscriptJSON
from app import db

from sqlalchemy import asc, desc
from app.auth.routes import protect_access


@bp.route("/transcribe", methods = ["GET", "POST"])
@protect_access
def transcribe():

    # Initiate the form, query the database for projects and update form choices
    transcribe_form = TranscribeForm()
    projects = Project.query.all()
    transcribe_form.select_project.choices = [('', '---')] + [(project.id, project.name) for project in projects]
    
    # GET requests
    if request.method == "GET":
        return render_template(
            "transcribe/transcribe.html", 
            transcribe_form=transcribe_form,
        )

    # POST requests
    # Scenario when the form is successfully submitted
    if transcribe_form.validate_on_submit():
        
        audio_file = request.files['file_upload']
        audio_file_path = f"./audio_files/{audio_file.filename}"
        audio_file.save(audio_file_path)
        
        if audio_file:

            # Submitting audio for transcription
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

            # AssemblyAI transcription configuration
            
            if transcribe_form.select_language.data == "auto":
                print("Detecting language automatically...")
                config = aai.TranscriptionConfig(
                    language_detection=True,
                    speaker_labels=True,
                    punctuate=True,
                    format_text=True,
                    #audio_end_at=120000, # 2 min
                )
            else:
                print(f"Submitting audio with lang code {transcribe_form.select_language.data}...")
                config = aai.TranscriptionConfig(
                    language_code=transcribe_form.select_language.data,
                    speaker_labels=True,
                    punctuate=True, 
                    format_text=True,
                    #audio_end_at=120000, # 2 min
                )

            # Initializing the transcriber
            transcriber = aai.Transcriber()

            # Submitting the audio file for transcription
            transcript = transcriber.submit(
                f"./audio_files/{audio_file.filename}",
                config=config,
            )
            
            # Create a new transcript object and add it to the database
            transcript_in_db = Transcript(
                assemblyai_id=transcript.id,
                audio_file_name=audio_file.filename,
                user_id=session["user_id"],
                transcription_status="submitted", # The status is set to "submitted" by default
                project_id=transcribe_form.select_project.data,
                # created_on is automatically set to the current date and time
            )

            db.session.add(transcript_in_db)
            db.session.commit()

            # Remove the audio file from the server
            os.remove(audio_file_path)

            return render_template(
                "transcribe/transcribe.html",
                transcribe_form=transcribe_form,
                transcription_successfully_submitted=True,
            )
    
    # Scenario when the form is not successfully submitted
    if request.method == 'POST' and not transcribe_form.validate_on_submit():

        return render_template(
                "transcribe/transcribe.html",
                transcribe_form=transcribe_form,
                transcription_successfully_submitted=False,
            )

@bp.route("/transcripts", methods = ["GET", "POST"])
@protect_access
def transcripts():

    transcripts = Transcript.query.order_by(desc(Transcript.date_created)).all()

    # Update the status of transcripts in the db and save the updated transcripts
    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    transcripts_handler.connect_check_update_and_save_transcripts(api_key)

    # POST requests only
    if request.method == "POST":
        # Printing transcripts to file
        transcript_id_download = transcripts_handler.get_transcript_id_from_multiple_forms(prefix='download_')
        if transcript_id_download:
            return transcripts_handler.write_transcript_to_file(transcript_id_download)
        
        # Deleting transcripts from db
        transcript_id_delete = transcripts_handler.get_transcript_id_from_multiple_forms(prefix='delete_')
        if transcript_id_delete:
            transcripts_handler.delete_transcript_from_db(transcript_id_delete)
            return redirect(url_for("transcribe.transcripts"))
        
    return render_template(
                "transcribe/transcripts.html",
                transcripts=transcripts,
                transcripts_being_processed=transcripts_handler.transcripts_being_processed,
            )

@bp.route('/_poll_transcripts_status', methods=['GET'])
@bp.route('/_poll_transcripts_status/<project_id>', methods=['GET'])
def _poll_transcripts_status(project_id=None):
    '''
    This route is used to poll the status of the transcripts in the AssemblyAI cloud
    when the user visits the /transcripts route.
    Project_id is an optional parameter that is used to filter 
    the transcripts based on the project_id. If no project_id is provided,
    the project_id is set to None and the route will return all transcripts.
    '''
    
    project_id = request.view_args.get('project_id')

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    changes_detected = transcripts_handler.connect_check_update_and_save_transcripts(api_key, project_id=project_id)

    return jsonify({"reload": changes_detected}), 200