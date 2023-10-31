
const ctx = document.getElementById('top-tokens-barchart').getContext('2d');
const myChart = new Chart(ctx, {
    type: 'bar',
    data: {
        labels: tokens, // ["a", "b", "c", "d"],
        datasets: [{
            //label: '# of tokens',
            data: token_counts, // [1, 2, 3, 4],
            backgroundColor: 'rgba(75, 192, 192, 0.2)',
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 1,
            barThickness: 15,
        }]
    },
    options: {
        indexAxis: 'y',
        plugins: {
            legend: {
                display: false
            },
        },
        scales: {
            x: {
                beginAtZero: true
            }
        }
    }
})

ngrams_field.addEventListener("change", () => {
    myChart.data.datasets[0].data = token_counts
    myChart.data.labels = tokens
    myChart.update()
})
