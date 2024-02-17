
function checkTranscriptsAndReload() {
    fetch(`/transcribe/check_transcripts_status`)
        .then(response => {
            return response.json()
        })
        .then(data => {
            if (data.reload) {
                window.location.reload()
            } else {
                setTimeout(checkTranscriptsAndReload, 5000)
            }
        })
        .catch(error => console.error('Error:', error));
}

checkTranscriptsAndReload()
