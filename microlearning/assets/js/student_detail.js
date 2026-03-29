/**
 * Student Drilldown - JavaScript
 * Extracted from student_detail.php for better maintainability
 */

// Global variables
let chartTrend = null;
let chartTimeAffinity = null;
let depthRowsAll = [];

// Cache configuration
const CACHE_KEY = 'student_drilldown_cache';
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
}

function formatDiffPct(v) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    const sign = v >= 0 ? '+' : '';
    return `${sign}${v.toFixed(1)}% vs class average`;
}

function destroyCharts() {
    if (chartTrend) { chartTrend.destroy(); chartTrend = null; }
    if (chartTimeAffinity) { chartTimeAffinity.destroy(); chartTimeAffinity = null; }
}

// ============================================================================
// CACHE MANAGEMENT
// ============================================================================

function getCachedData(studentKey, courseKey) {
    try {
        const cacheStr = sessionStorage.getItem(CACHE_KEY);
        if (!cacheStr) return null;
        
        const cache = JSON.parse(cacheStr);
        const cacheKey = `${studentKey}_${courseKey}`;
        const cached = cache[cacheKey];
        
        if (!cached) return null;
        
        const now = Date.now();
        if (now - cached.timestamp > CACHE_DURATION) {
            delete cache[cacheKey];
            sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
            return null;
        }
        
        return cached.data;
    } catch (error) {
        console.error('Cache read error:', error);
        return null;
    }
}

function setCachedData(studentKey, courseKey, data) {
    try {
        const cacheStr = sessionStorage.getItem(CACHE_KEY);
        const cache = cacheStr ? JSON.parse(cacheStr) : {};
        const cacheKey = `${studentKey}_${courseKey}`;
        
        cache[cacheKey] = {
            data: data,
            timestamp: Date.now()
        };
        
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
        console.error('Cache write error:', error);
    }
}

function clearCache(studentKey, courseKey) {
    try {
        const cacheStr = sessionStorage.getItem(CACHE_KEY);
        if (!cacheStr) return;
        
        const cache = JSON.parse(cacheStr);
        const cacheKey = `${studentKey}_${courseKey}`;
        delete cache[cacheKey];
        
        sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
    } catch (error) {
        console.error('Cache clear error:', error);
    }
}

// ============================================================================
// CHART RENDERING FUNCTIONS
// ============================================================================

function identifyBestTimeSlot(timeAffinityData) {
    if (!timeAffinityData || timeAffinityData.length === 0) return null;
    
    let bestSlot = timeAffinityData[0];
    for (let i = 1; i < timeAffinityData.length; i++) {
        const currentEfficiency = parseFloat(timeAffinityData[i].efficiency_index) || 0;
        const bestEfficiency = parseFloat(bestSlot.efficiency_index) || 0;
        
        if (currentEfficiency > bestEfficiency) {
            bestSlot = timeAffinityData[i];
        }
    }
    
    return {
        bestSlot: bestSlot.time_slot,
        bestEfficiency: parseFloat(bestSlot.efficiency_index),
        recommendation: `Student learns best during ${bestSlot.time_slot}`
    };
}

function renderTimeAffinityChart(timeAffinityData) {
    if (!timeAffinityData || timeAffinityData.length === 0) return;
    
    document.getElementById('time-affinity-section').classList.remove('hidden');
    
    const bestTimeInfo = identifyBestTimeSlot(timeAffinityData);
    if (bestTimeInfo) {
        document.getElementById('time-recommendation-text').textContent = bestTimeInfo.recommendation;
    }
    
    const categories = [];
    const efficiencyData = [];
    const colors = [];
    
    timeAffinityData.forEach(item => {
        categories.push(item.time_slot);
        const efficiency = parseFloat(item.efficiency_index) || 0;
        efficiencyData.push(efficiency);
        colors.push(bestTimeInfo && item.time_slot === bestTimeInfo.bestSlot ? '#6366f1' : '#94a3b8');
    });
    
    const options = {
        series: [{ name: 'Efficiency Index', data: efficiencyData }],
        chart: { type: 'bar', height: 350, toolbar: { show: true } },
        plotOptions: { bar: { borderRadius: 8, distributed: true, dataLabels: { position: 'top' } } },
        colors: colors,
        dataLabels: {
            enabled: true,
            formatter: (val) => val.toFixed(2),
            offsetY: -25,
            style: { fontSize: '12px', fontWeight: 600, colors: ['#475569'] }
        },
        xaxis: {
            categories: categories,
            title: { text: 'Time Slot', style: { fontSize: '14px', fontWeight: 600, color: '#475569' } }
        },
        yaxis: {
            title: { text: 'Efficiency Index', style: { fontSize: '14px', fontWeight: 600, color: '#475569' } }
        },
        legend: { show: false },
        title: { text: 'Learning Efficiency by Time of Day', align: 'left', style: { fontSize: '16px', fontWeight: 600 } }
    };
    
    document.querySelector("#time-affinity-chart").innerHTML = '';
    if (chartTimeAffinity) { chartTimeAffinity.destroy(); chartTimeAffinity = null; }
    chartTimeAffinity = new ApexCharts(document.querySelector("#time-affinity-chart"), options);
    chartTimeAffinity.render();
}

function renderEngagementTrendChart(studentData, classData) {
    if (!studentData || studentData.length === 0) {
        document.getElementById('engagement-trend-section').classList.add('hidden');
        return;
    }
    document.getElementById('engagement-trend-section').classList.remove('hidden');

    classData = classData || [];
    const classAverageMap = {};
    classData.forEach(item => {
        const key = `${item.year}-${item.week_of_year}`;
        classAverageMap[key] = parseFloat(item.avg_engagement_score) || 0;
    });
    
    const categories = [];
    const studentSeries = [];
    const classSeries = [];
    const riskDiscrete = [];
    const crammingAnnotations = [];
    
    studentData.forEach((item, idx) => {
        const weekLabel = `W${item.week_of_year} ${item.year}`;
        categories.push(weekLabel);
        
        const score = parseInt(item.engagement_score) || 0;
        studentSeries.push(score);
        
        const key = `${item.year}-${item.week_of_year}`;
        classSeries.push(classAverageMap[key] || 0);

        if (item.risk_level === 'High') {
            riskDiscrete.push({
                seriesIndex: 0,
                dataPointIndex: idx,
                fillColor: '#ef4444',
                strokeColor: '#fff',
                size: 7
            });
        }
        
        // Cramming detection
        if (idx > 0) {
            const previousScore = studentSeries[idx - 1];
            if (previousScore > 0) {
                const increasePercentage = ((score - previousScore) / previousScore) * 100;
                if (increasePercentage > 300) {
                    crammingAnnotations.push({
                        x: weekLabel,
                        borderColor: '#f59e0b',
                        label: {
                            borderColor: '#f59e0b',
                            style: { color: '#fff', background: '#f59e0b' },
                            text: 'Cramming'
                        }
                    });
                }
            }
        }
    });
    
    const options = {
        series: [
            { name: 'Student Engagement', data: studentSeries, color: '#6366f1' },
            { name: 'Class Average', data: classSeries, color: '#94a3b8' }
        ],
        chart: { type: 'line', height: 350, toolbar: { show: true } },
        annotations: { xaxis: crammingAnnotations },
        stroke: { width: [3, 2], curve: 'smooth', dashArray: [0, 5] },
        markers: { size: [5, 0], strokeWidth: 2, discrete: riskDiscrete },
        xaxis: { categories: categories, title: { text: 'Week' } },
        yaxis: { title: { text: 'Engagement Score' }, min: 0, max: 100 },
        legend: { position: 'top', horizontalAlign: 'right' }
    };
    
    document.querySelector("#engagement-trend-chart").innerHTML = '';
    if (chartTrend) { chartTrend.destroy(); chartTrend = null; }
    chartTrend = new ApexCharts(document.querySelector("#engagement-trend-chart"), options);
    chartTrend.render();
}

// ============================================================================
// RENDERING FUNCTIONS (Continued in next file due to length)
// ============================================================================

// Export for use in HTML
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        getCachedData,
        setCachedData,
        clearCache,
        renderTimeAffinityChart,
        renderEngagementTrendChart
    };
}
