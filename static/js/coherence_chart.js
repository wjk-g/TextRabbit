const ctx = document.getElementById('coherence-chart').getContext('2d');
const myLineChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            //label: 'Spójność klastrów',
            data: data,
            borderColor: '#FF5733',
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
