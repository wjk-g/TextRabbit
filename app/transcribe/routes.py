import os

import assemblyai as aai

# Flask imports
from flask import Flask, render_template, session, request, jsonify

# Load forms
from app.transcribe.forms import TranscribeForm

# Load classes
from app.nlp.data import Data
from app.nlp.routes import initiate_storage

from app.transcribe.transcripts_handler import TranscriptsHandler

from app.transcribe import bp
from app.auth.routes import protect_access

from app.models import Project, User, Transcript, TranscriptJSON
from app import db


@bp.route("/transcribe", methods = ["GET", "POST"])
@protect_access
def transcribe():
    
    d = session.get('d')

    # Initiate the form, query the database for projects and update form choices
    transcribe_form = TranscribeForm()
    projects = Project.query.all()
    transcribe_form.select_project.choices = [('', '---')] + [(project.id, project.name) for project in projects]
    
    # GET requests
    if request.method == "GET":
        return render_template(
            "transcribe/transcribe2.html", 
            d=d,
            storage=initiate_storage(),
            transcribe_form=transcribe_form,
            request_method=request.method,
            form_valid=True, # form_valid variable is required by the template when handling POST requests
        )

    # POST requests
    # Scenario when the form is successfully submitted
    if transcribe_form.validate_on_submit():

        form_valid = True
        transcription_successfully_submitted = False
        
        audio_file = request.files['file_upload']
        audio_file.save(f"./audio_files/{audio_file.filename}") # TODO delete files after they're submitted for transcritption
        
        if audio_file:

            # Submitting audio for transcription
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

            # AssemblyAI transcription configuration
            config = aai.TranscriptionConfig(
                language_code=transcribe_form.select_language.data,
                speaker_labels=True,
                punctuate=True, 
                format_text=True,
            )

            # Initializing the transcriber
            transcriber = aai.Transcriber()

            # Submitting the audio file for transcription
            transcript = transcriber.submit(
                f"./audio_files/{audio_file.filename}",
                config=config,
            )

            # Changing the value of the `transcription_successfully_submitted` flag to True
            transcription_successfully_submitted = True
            
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

            return render_template(
                "transcribe/transcribe2.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                form_valid=form_valid,
                request_method=request.method,
                transcription_successfully_submitted=transcription_successfully_submitted,
            )
    
    # Scenario when the form is not successfully submitted
    if request.method == 'POST' and not transcribe_form.validate_on_submit():
        
        form_valid = False
        transcription_successfully_submitted = False

        return render_template(
                "transcribe/transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                form_valid=form_valid,
                request_method=request.method,
                transcription_successfully_submitted=transcription_successfully_submitted,
            )

@bp.route("/transcripts", methods = ["GET", "POST"])
@protect_access
def transcripts():

    d = session.get("d", Data({}))

    transcripts = Transcript.query.all()

    # Update the status of transcripts in the db and save the updated transcripts
    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    transcripts_handler.connect_check_update_and_save_transcripts(api_key)

    # POST requests
    if request.method == "POST":
        for key in request.form:
            if key.startswith('download_'):
                transcript_id = key.split('_')[1]
                return transcripts_handler.write_transcript_to_file(transcript_id)

    return render_template(
                "transcribe/transcripts.html", 
                d=d,
                storage=initiate_storage(),
                transcripts=transcripts,
                transcripts_being_processed=transcripts_handler.transcripts_being_processed,
            )

@bp.route('/_poll_transcripts_status', methods=['GET'])
def _poll_transcripts_status():
    '''
    This route is used to poll the status of the transcripts in the AssemblyAI cloud
    when the user visits the /transcripts route.
    '''

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    changes_detected = transcripts_handler.connect_check_update_and_save_transcripts(api_key)

    return jsonify({"reload": changes_detected}), 200