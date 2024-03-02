import os

import assemblyai as aai

# Flask imports
from flask import Flask, render_template, session, request, jsonify

# Load forms
from app.transcribe.forms import TranscribeForm

# Load classes
from app.nlp.data import Data
from app.nlp.routes import initiate_storage

from app.transcribe.transcripts import TranscriptsHandler

from app.transcribe import bp
from app.auth.routes import protect_access

from app.models import Project, User, Transcript
from app import db


@bp.route("/transcribe", methods = ["GET", "POST"])
@protect_access
def transcribe():
    
    d = session.get('d')
    transcribe_form = TranscribeForm()
    
    if request.method == "GET":
        return render_template(
            "transcribe/transcribe.html", 
            d=d,
            storage=initiate_storage(),
            transcribe_form=transcribe_form,
            user_transcripts = session.get("user_transcripts", ""),
            request_method=request.method,
            form_valid=True,
        )

    if transcribe_form.validate_on_submit():

        form_valid = True
        transcription_submitted = False
        
        audio_file = request.files['file_upload']
        #print(audio_file)
        #TODO change the name of the folder
        #TODO automatically delete files after they're submitted for transcritption
        audio_file.save(f"./audio_files/{audio_file.filename}")
        
        if audio_file:
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')
            config = aai.TranscriptionConfig(
                language_code=transcribe_form.select_language.data,
                speaker_labels=True,
                punctuate=True, 
                format_text=True,
            )

            transcriber = aai.Transcriber()

            transcript = transcriber.submit(
                f"./test_audio/{audio_file.filename}",
                config=config,
            )

            transcript_id = transcript.id

            if session.get("transcripts_in_session_ids"):
                session["transcripts_in_session_ids"].append(transcript_id)
            else:
                session["transcripts_in_session_ids"] = [transcript_id]

            transcription_submitted = True
        
            return render_template(
                "transcribe/transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )
        
    if request.method == 'POST' and not transcribe_form.validate_on_submit():
        
        form_valid = False
        transcription_submitted = False

        return render_template(
                "transcribe/transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )

@bp.route("/retrieve_transcripts", methods = ["GET", "POST"])
@protect_access
def retrieve_transcripts():
    
    d = session.get("d")

    transcripts_handler = TranscriptsHandler()

    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    
    transcripts_in_session_ids = session.get("transcripts_in_session_ids")

    transcripts_in_session = []

    transcripts_being_processed = []
    session["transcripts_being_processed"] = transcripts_being_processed

    # TODO duplicated, put it in a function
    if transcripts_in_session_ids:
        transcripts_handler.get_response_from_api(api_key=api_key, limit=100)
        transcripts_handler.get_transcripts_in_session(transcripts_in_session_ids)
        
        # All transcripts in session
        transcripts_in_session = transcripts_handler.transcripts_in_session

        # All transcripts being processed
        transcripts_being_processed = [t["id"] for t in transcripts_in_session if t["status"] == "processing"]

        session["transcripts_being_processed"] = transcripts_being_processed
        # example: {"status": "processing", "id": 123}, {"status": "processing", "id": 456}

    if request.method == "POST":
        for key in request.form:
            if key.startswith('download_'):
                transcript_id = key.split('_')[1]
                return transcripts_handler.download_transcript(transcript_id)

    return render_template(
        "transcribe/retrieve_transcripts.html", 
        d=d,
        storage=initiate_storage(),
        transcripts=transcripts_in_session,
        transcripts_being_processed=transcripts_being_processed,
        user_transcripts = session.get("transcripts_in_session_ids"),
    )

@bp.route('/check_transcripts_status', methods=['GET'])
def check_transcripts_status():

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')
    # TODO Get transcripts being processed from the db
    # So with a different status than "submitted" or "error"
    # Przy każdym wejściu na stronę z transkrypcjami musimy sprawdzić wszystkie
    # "processing..." i uaktualnić statusy. A 
    transcripts_being_processed = session.get("transcripts_being_processed")

    transcripts_handler.get_response_from_api(api_key=api_key, limit=100)

    transcripts_statuses = [ transcripts_handler.get_transcript_status(t) for t in transcripts_being_processed ]

    if transcripts_statuses:
        is_completed = any(status != 'processing' for status in transcripts_statuses)
    else:
        is_completed = False

    return jsonify({"reload": is_completed}), 200


@bp.route("/transcribe2", methods = ["GET", "POST"])
@protect_access
def transcribe2():
    
    d = session.get('d')
    transcribe_form = TranscribeForm()

    # Query the database for projects and update form choices
    projects = Project.query.all()
    transcribe_form.select_project.choices = [('', '---')] + [(project.id, project.name) for project in projects]
    
    if request.method == "GET":
        return render_template(
            "transcribe/transcribe2.html", 
            d=d,
            storage=initiate_storage(),
            transcribe_form=transcribe_form,
            user_transcripts = session.get("user_transcripts", ""),
            request_method=request.method,
            form_valid=True,
        )

    if transcribe_form.validate_on_submit():

        form_valid = True
        transcription_submitted = False
        
        audio_file = request.files['file_upload']
        #print(audio_file)
        #TODO change the name of the folder
        #TODO automatically delete files after they're submitted for transcritption
        audio_file.save(f"./audio_files/{audio_file.filename}")
        
        if audio_file:

            # Submitting audio for transcription
            aai.settings.api_key = os.getenv('ASSEMBLYAI_API_KEY')

            config = aai.TranscriptionConfig(
                language_code=transcribe_form.select_language.data,
                speaker_labels=True,
                punctuate=True, 
                format_text=True,
            )

            transcriber = aai.Transcriber()

            transcript = transcriber.submit(
                f"./audio_files/{audio_file.filename}",
                config=config,
            )

            # Create a new Transcript instance

            # Checking task current status

            transcripts_handler = TranscriptsHandler()
            transcripts_handler.get_response_from_api(aai.settings.api_key)
            transcript_status = transcripts_handler.get_transcript_status(transcript.id)
            print(transcript_status)

            transcript_in_db = Transcript(
                assemblyai_id=transcript.id,
                audio_file_name=audio_file.filename,
                user_id=session["user_id"],
                #error_message=data.get('error_message'),  # Optional field
                transcription_status=transcript_status,
                project_id=transcribe_form.select_project.data,
                # created_on is automatically set to the current date and time
            )

            # Add the new transcript to the session and commit
            db.session.add(transcript_in_db)
            db.session.commit()

            return render_template(
                "transcribe/transcribe2.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )
        
    if request.method == 'POST' and not transcribe_form.validate_on_submit():
        
        form_valid = False
        transcription_submitted = False

        return render_template(
                "transcribe/transcribe.html", 
                d=d,
                storage=initiate_storage(),
                transcribe_form=transcribe_form,
                #user_transcripts = session.get("user_transcripts", ""),
                transcription_submitted=transcription_submitted,
                form_valid=form_valid,
                request_method=request.method,
            )
    
def check_statuses_of_transcripts_in_db(transcripts):
    transcripts_being_processed = [t.assemblyai_id for t in transcripts if t.transcription_status == "processing"]
    return transcripts_being_processed

@bp.route("/transcripts", methods = ["GET", "POST"])
@protect_access
def transcripts():

    d = session.get("d", Data({}))

    transcripts = Transcript.query.all()
    
    transcripts_being_processed = check_statuses_of_transcripts_in_db(transcripts)

    return render_template(
                "transcribe/transcripts.html", 
                d=d,
                storage=initiate_storage(),
                transcripts=transcripts,
                transcripts_being_processed=transcripts_being_processed,
            )
