import requests
import os

error_id = "c8c6e44b-106f-417d-af8d-a9ec0675231f"
api_key = os.getenv('ASSEMBLYAI_API_KEY')

url = "https://api.assemblyai.com/v2/transcript"

headers = {
    "authorization": api_key,
    "content-type": "application/json"
}

def download_transcript(transcript_id):
        
    endpoint = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"

    response = requests.get(endpoint, headers=headers)
    return response.json()

json = download_transcript(error_id)
print(json)