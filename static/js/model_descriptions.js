// Model selection 
const selection = document.querySelector("#select_model")
const descriptions = document.querySelectorAll(".model-description")

descriptions.forEach(description => {
    if (description.id === selection.value) {
        description.classList.remove("d-none")
    }
})

selection.addEventListener("change", () => {
    //console.log(selection.value)
    descriptions.forEach(description => {
        if (description.id === selection.value) {
            descriptions.forEach(description => description.classList.add("d-none"))
            description.classList.remove("d-none")
        }
    })
})