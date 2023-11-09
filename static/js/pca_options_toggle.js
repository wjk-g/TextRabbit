// PCA radio
const pca_radio_yes = document.querySelector("#pca_radio-0")
const pca_radio_no = document.querySelector("#pca_radio-1")
const pca_div = document.querySelector(".pca")

pca_radio_yes.addEventListener("click", () => {
    pca_div.classList.remove("d-none")
})

pca_radio_no.addEventListener("click", () => {
    pca_div.classList.add("d-none")
})

console.log(pca_radio)