
function checkTranscriptsAndReload() {
    fetch(`/check_transcripts_status`)
        .then(response => {
            return response.json()
        })
        .then(data => {
            console.log(data)
            if (data.reload) {
                console.log("reload!")
                window.location.reload()
            } else {
                console.log("wiating 5 seconds")
                setTimeout(checkTranscriptsAndReload, 5000)
            }
        })
        .catch(error => console.error('Error:', error));
}

checkTranscriptsAndReload()
