
function checkTranscriptsAndReload(project_id) {
    
    let url = `/transcribe/_poll_transcripts_status`;
    if (project_id) {
        url += `/${project_id}`;
    }

    fetch(url)
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

//check if project_id is defined in the window object
if (window.hasOwnProperty('project_id')) {
    // run checkTranscripts... for a single project
    checkTranscriptsAndReload(project_id)
} else {
    // run checkTranscripts... for all projects
    checkTranscriptsAndReload()
}
