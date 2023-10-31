// Model selection 
const selection = document.querySelector("#select_model")
const descriptions = document.querySelectorAll(".model-description")

descriptions.forEach(description => {
    if (description.id === selection.value) {
        description.classList.add("show")
    }
})

selection.addEventListener("change", () => {
    //console.log(selection.value)
    descriptions.forEach(description => {
        if (description.id === selection.value) {
            descriptions.forEach(description => description.classList.remove("show"))
            description.classList.add("show")
        }
    })
})