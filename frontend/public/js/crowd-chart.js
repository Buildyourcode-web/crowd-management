/**
 * Chart.js Hourly Crowd Trend Controller
 */
class CrowdChartController {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chart = null;
        
        // Custom in-place plugin to draw values above bars
        this.barLabelsPlugin = {
            id: 'barLabels',
            afterDatasetsDraw(chart) {
                const { ctx } = chart;
                ctx.save();
                ctx.font = 'bold 12px "Outfit", sans-serif';
                ctx.fillStyle = '#475569';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'bottom';

                chart.data.datasets.forEach((dataset, i) => {
                    const meta = chart.getDatasetMeta(i);
                    meta.data.forEach((bar, index) => {
                        const value = dataset.data[index];
                        // Only draw if value > 0
                        if (value > 0) {
                            ctx.fillText(value.toLocaleString(), bar.x, bar.y - 5);
                        }
                    });
                });
                ctx.restore();
            }
        };
    }

    /**
     * Initialize or update the chart.
     */
    render(labels, dataValues) {
        const ctx = document.getElementById(this.canvasId);
        if (!ctx) return;

        // If chart already exists, destroy it before rebuilding to avoid duplicate rendering overlays
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Crowd Count',
                    data: dataValues,
                    backgroundColor: '#3b82f6', // Solid blue color matching reference
                    hoverBackgroundColor: '#2563eb',
                    borderRadius: 8, // Rounded bars
                    borderSkipped: false,
                    barPercentage: 0.5,
                    categoryPercentage: 0.8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false // Hide legend
                    },
                    tooltip: {
                        enabled: true,
                        callbacks: {
                            label: function(context) {
                                return `Count: ${context.parsed.y.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            font: {
                                family: 'Outfit',
                                size: 12,
                                weight: '500'
                            },
                            color: '#64748b'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#f1f5f9'
                        },
                        ticks: {
                            font: {
                                family: 'Outfit',
                                size: 12
                            },
                            color: '#94a3b8',
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        },
                        suggestedMax: Math.max(...dataValues, 100) * 1.15 // Give space for numbers above bars
                    }
                }
            },
            plugins: [this.barLabelsPlugin]
        });
    }

    /**
     * Dynamic update helper
     */
    updateData(labels, dataValues) {
        if (this.chart) {
            this.chart.data.labels = labels;
            this.chart.data.datasets[0].data = dataValues;
            
            // Adjust y-axis max limit dynamically to ensure numbers fit
            if (this.chart.options.scales.y) {
                this.chart.options.scales.y.suggestedMax = Math.max(...dataValues, 100) * 1.15;
            }
            
            this.chart.update();
        } else {
            this.render(labels, dataValues);
        }
    }
}

// Instantiate and expose globally
window.crowdChart = new CrowdChartController('crowd-trend-chart');
