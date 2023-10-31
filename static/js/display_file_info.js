// Get the file input element
const fileInput = document.getElementById('file');

// Get the file info element
const fileInfo = document.getElementById('fileInfo');

// Add event listener for the onchange event
file.addEventListener('change', handleFileUpload);

// Function to handle the file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    
    // Convert file size to megabytes
    const fileSizeMB = (file.size / (1024 * 1024)).toFixed(2);

    // Display file information
    fileInfo.innerHTML = `
        <p>Nazwa pliku: <strong>${file.name}</strong></p>
        <p>Rozmiar pliku: <strong>${fileSizeMB} MB</strong></p>
    `;
    
    // Use FileReader to read file contents
    const reader = new FileReader();
    reader.onload = function(e) {
        const fileContent = e.target.result;

        // Display file content
        console.log('File Content:', fileContent);
    };
    reader.readAsText(file);
}