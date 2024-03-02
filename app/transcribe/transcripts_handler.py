import requests
from flask import send_file

from app import db
from app.models import User, Project, Transcript, TranscriptJSON


class TranscriptsHandler():
    def __init__(self):
        self.transcripts_in_session = [] # TODO REMOVE
        self.transcripts_being_processed = []
        self.response = {}
        self.headers = {}

    def get_response_from_api(self, api_key, limit=50):
        url = "https://api.assemblyai.com/v2/transcript"
        
        params = {
            'limit': limit
        }

        headers = {
            "authorization": api_key,
            "content-type": "application/json"
        }
        self.headers = headers
        self.response = requests.get(url, headers=headers, params=params)

    def get_transcript_status(self, transcript_id):

        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(polling_endpoint, headers=self.headers).json()
        return response['status']
    
    def get_transcripts_with_processing_status_in_db(self):
        transcripts_being_processed = db.session.query(Transcript).filter(Transcript.transcription_status == "processing").all()
        self.transcripts_being_processed = transcripts_being_processed
        return transcripts_being_processed
    
    def check_and_update_current_status_of_transcripts(self):

        # Set flag for changes in status
        changes_in_status = False

        for transcript in self.transcripts_being_processed:
            print("Transcript")
            print(transcript)
            print(transcript.assemblyai_id)
            # Get current status from AssemblyAI
            current_status = self.get_transcript_status(transcript.assemblyai_id)
            print("Current status")
            print(current_status)
            # Update status in db if status does not equal "processing"
            if current_status != "processing":
                self.update_transcript_status(transcript, new_status=current_status)
                changes_in_status = True
        
        return changes_in_status

    def update_transcript_status(self, transcript, new_status):
        transcript.transcription_status = new_status
        db.session.commit()

    def download_transcript(self, transcript_id):

        def convert_ms_to_hms(milliseconds):
            seconds, milliseconds = divmod(milliseconds, 1000)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        
        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

        response = requests.get(endpoint, headers=self.headers)
        
        utterances = response.json().get("utterances")

        transcript_text = ""
        
        for utterance in utterances:
            start_time_formatted = convert_ms_to_hms(utterance.get("start"))
            end_time_formatted = convert_ms_to_hms(utterance.get("end"))
            speaker = utterance.get("speaker")
            utterance_text = utterance.get("text")
            transcript_text += f"[{start_time_formatted}-{end_time_formatted}] SPEAKER {speaker}: {utterance_text}\n\n"
        
        # Writing to the file
        with open('app/transcribe/uploads/transcript.txt', 'w') as file:
            file.write(transcript_text)

        return send_file('transcribe/uploads/transcript.txt', as_attachment=True)

    def delete_transcript(self, transcript_id):
        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

        response = requests.delete(endpoint, headers=self.headers)
