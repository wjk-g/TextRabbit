const ctx = document.getElementById('coherence-chart').getContext('2d');
const myLineChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            //label: 'Spójność klastrów',
            data: data,
            borderColor: 'rgba(210, 147, 183, 1)',
            fill: false
        }]
    },
    options: {
        plugins: {
            legend: {
                display: false
            },
        },
        scales: {
            y: {
                beginAtZero: false
            }
        }
    }
});
