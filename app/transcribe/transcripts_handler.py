import requests
from flask import send_file, request

from app import db
from app.models import User, Project, Transcript, TranscriptJSON


class TranscriptsHandler():
    def __init__(self):
        self.transcripts_being_processed = []
        self.updated_transcripts = []
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

    # Functions for communicating with assemblyAI API and updating db
    
    def get_transcript_status(self, transcript_id):
        ''' 
        Get status of a single transcript based on its AssemblyAI id
        '''

        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(polling_endpoint, headers=self.headers).json()
        return response['status']
    
    def get_transcripts_with_submitted_status_in_db(self, project_id=None):
        '''
        Get transcripts with status "submitted" or "processing" from the db
        '''

        # if project_id is provided, get all transcripts with status "submitted" or "processing" for that project 
        if project_id:
            transcripts_being_processed = db.session.query(
                Transcript).filter(
                Transcript.transcription_status.in_(["submitted", "processing"]),
                Transcript.project_id == project_id
            ).all()
            print("if project_id: get_transcripts_with_submitted_status_in_db", self.transcripts_being_processed) # Debug
            self.transcripts_being_processed = transcripts_being_processed
            return transcripts_being_processed
        
        # if project_id not provided, get all transcripts with status "submitted" or "processing"     
        print("else: get_transcripts_with_submitted_status_in_db", self.transcripts_being_processed) # Debug
        transcripts_being_processed = db.session.query(Transcript).filter(Transcript.transcription_status.in_(["submitted", "processing"])).all()
        self.transcripts_being_processed = transcripts_being_processed
        return transcripts_being_processed
    
    def check_and_update_current_status_of_transcripts(self):
        '''
        Update the status of transcripts with status = "submitted" or "processing" in the db
        If a status different than "submitted" is detected, updates are made
        and the function returns True. Otherwise, it returns False.
        '''

        # Set flag for changes in status
        changes_in_status = False

        for transcript in self.transcripts_being_processed:
            
            status_in_db = transcript.transcription_status
            aai_status = self.get_transcript_status(transcript.assemblyai_id)

            # Update status in db if status does not equal "processing"
            if aai_status != status_in_db:
                self.update_transcript_status(transcript, new_status=aai_status)
                changes_in_status = True
        
        return changes_in_status

    def update_transcript_status(self, transcript, new_status):
        '''
        Update the status of a single status in the db
        '''
        transcript.transcription_status = new_status
        db.session.commit()

    def download_json_payload(self, transcript_id):
        '''
        Download the json payload for a single transcript based on transcript_id
        '''

        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(endpoint, headers=self.headers)
        json_payload = response.json()
        
        return json_payload
    

    def add_updated_transcripts_to_db(self):
        for transcript in self.transcripts_being_processed:
            # Download JSON payload for updated transcripts and add it to the db
            if transcript.transcription_status != "submitted" and transcript.transcription_status != "processing":
                print("Initiating download of JSON payload for completed transcripts...")
                json_payload = self.download_json_payload(transcript.assemblyai_id)

                transcript_json = TranscriptJSON(
                    assemblyai_id=transcript.assemblyai_id,
                    json_content=json_payload,
                )

                db.session.add(transcript_json)
                db.session.commit()
                print(f"JSON payload for {transcript.assemblyai_id} has been added to the database.")

    def connect_check_update_and_save_transcripts(self, api_key, project_id=None):
        '''
        This method brings together the methods for: 
        - checking the status of transcripts
        - updating the status of transcripts
        - adding updated transcripts to the db
        Returns True if changes in status are detected, otherwise False
        '''
        self.get_response_from_api(api_key=api_key, limit=100)
        self.get_transcripts_with_submitted_status_in_db(project_id=project_id)
        changes_detected = self.check_and_update_current_status_of_transcripts()
        if changes_detected:
            self.add_updated_transcripts_to_db()
        
        return changes_detected

    @staticmethod
    def get_transcript_id_from_multiple_forms(prefix):
            for key in request.form:
                if key.startswith(prefix):
                    transcript_id = key.split('_')[1]
                    return transcript_id
            return None

    def write_transcript_to_file(self, transcript_id):

        def convert_ms_to_hms(milliseconds):
            seconds, milliseconds = divmod(milliseconds, 1000)
            minutes, seconds = divmod(seconds, 60)
            hours, minutes = divmod(minutes, 60)
            return f"{hours:02}:{minutes:02}:{seconds:02}"
        
        transcript = db.session.query(Transcript).filter(Transcript.assemblyai_id == transcript_id).first()
        transcript_json = db.session.query(TranscriptJSON).filter(TranscriptJSON.assemblyai_id == transcript_id).first()

        utterances = transcript_json.json_content.get("utterances")

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

    @staticmethod
    def delete_transcript_from_db(transcript_id):
        transcript = db.session.query(
            Transcript
        ).filter(Transcript.assemblyai_id == transcript_id).first()
        
        db.session.delete(transcript)
        db.session.commit()
