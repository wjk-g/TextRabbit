import requests
from flask import send_file

class TranscriptsHandler():
    def __init__(self):
        self.transcripts_in_session = []
        #self.transcripts_details = []
        #self.transcript_count = 0
        #self.last_transcript_created_on = ""
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

    def get_transcripts_in_session(self, transcripts_in_session_ids):

        if self.response.status_code == 200:
            all_transcripts = self.response.json()["transcripts"]
        else:
            return f"Error: {self.response.status_code}"
        
        self.transcripts_in_session = [transcript for transcript in all_transcripts if transcript["id"] in transcripts_in_session_ids]
    
    def get_transcript_status(self, transcript_id):

        polling_endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        response = requests.get(polling_endpoint, headers=self.headers).json()
        return response['status']

    #def create_detailed_transcripts_list(self):

    #    for transcript in self.transcripts_list:
    #        transcript_id = transcript["id"]
    #        #print(transcript_id)
    #        #print(transcript)
    #        endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
    #        response = requests.get(endpoint, headers=self.headers)
    #        full_response = response.json()
    #        full_response["created"] = transcript["created"]
    #        full_response["completed"] = transcript["completed"]
    #        full_response["audio_duration_in_minutes"] = round(full_response["audio_duration"] / 60, 2) 
    #        self.transcripts_details.append(full_response)
    #        #print(self.transcripts_details)
            #print(type(self.transcripts_details))

    #def get_detailed_transcripts_list(self):
    #    for transcript in self.transcripts_details:
    #        print(transcript)

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
