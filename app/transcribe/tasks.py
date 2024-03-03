import os
import time

from app.transcribe.transcripts_handler import TranscriptsHandler

from app import create_app


app = create_app()
app.app_context().push()

def update_and_download_transcripts():

    transcripts_handler = TranscriptsHandler()
    api_key = os.getenv('ASSEMBLYAI_API_KEY')

    transcripts_handler.get_response_from_api(api_key=api_key, limit=100)
    transcripts_handler.get_transcripts_with_processing_status_in_db()

    if transcripts_handler.transcripts_being_processed:
        print("Detected new transcripts")
        print("Applying changes to the database...")
        transcripts_handler.check_and_update_current_status_of_transcripts()
        print("Changed transcripts status")
    
    print("Nothing to update at the moment")

    time.sleep(60*60) # 1 hour
