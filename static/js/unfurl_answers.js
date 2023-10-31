const question_answer_blocks = document.querySelectorAll("#question-answer-block")
const answers = document.querySelectorAll("#answer")

console.log(question_answer_blocks)

question_answer_blocks.forEach(block =>{ 
    console.log(block)
    block.querySelector("#question-button").addEventListener("click", event => {
        answers.forEach(answer => {
            answer.classList.remove("show")
        })
        block.querySelector("#answer").classList.toggle("show")

    })
})