import os
import time

from app.transcribe.transcripts_handler import TranscriptsHandler

from app import create_app


app = create_app()
app.app_context().push()

def update_and_download_transcripts():

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')

    changes_detected = transcripts_handler.connect_check_update_and_save_transcripts(api_key)
    
    if changes_detected:
        print("Updating the database...")
    else:    
        print("Nothing to update at the moment")

    time.sleep(60*60) # 1 hour
