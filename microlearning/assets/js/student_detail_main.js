/**
 * Student Drilldown - Main Application Logic
 * Progressive loading, data fetching, and initialization
 */

// ============================================================================
// PROGRESSIVE LOADING
// ============================================================================

function applyStudentDataProgressive(data) {
    // Phase 1: Load overview metrics immediately
    document.getElementById('loading-state').classList.add('hidden');
    document.getElementById('error-state').classList.add('hidden');
    document.getElementById('overview-metrics').classList.remove('hidden');

    const overview = data.overview;
    
    // Apply overview metrics
    document.getElementById('engagement-score').textContent = overview.engagement_score;
    document.getElementById('risk-level').textContent = overview.risk_level;
    document.getElementById('dropout-probability').textContent =
        `${overview.dropout_probability_pct.toFixed(1)}% dropout probability`;

    // Risk indicators
    const riskIndicator = document.getElementById('risk-indicator');
    const riskIcon = document.getElementById('risk-icon');
    riskIndicator.className = 'hidden w-3 h-3 rounded-full';
    riskIcon.className = 'flex-shrink-0 w-12 h-12 rounded-xl bg-slate-50 flex items-center justify-center';
    riskIcon.querySelector('svg').setAttribute('class', 'w-6 h-6 text-slate-600');

    const riskColors = {
        'High': { indicator: 'bg-red-500', icon: 'bg-red-50', svg: 'text-red-600' },
        'Medium': { indicator: 'bg-yellow-500', icon: 'bg-yellow-50', svg: 'text-yellow-600' },
        'Low': { indicator: 'bg-green-500', icon: 'bg-green-50', svg: 'text-green-600' }
    };

    if (riskColors[overview.risk_level]) {
        const colors = riskColors[overview.risk_level];
        riskIndicator.classList.remove('hidden');
        riskIndicator.classList.add(colors.indicator);
        riskIcon.classList.remove('bg-slate-50');
        riskIcon.classList.add(colors.icon);
        riskIcon.querySelector('svg').classList.remove('text-slate-600');
        riskIcon.querySelector('svg').classList.add(colors.svg);
    }

    // Progress
    const progressPct = overview.current_progress_pct;
    document.getElementById('progress-pct').textContent = `${progressPct}%`;
    document.getElementById('progress-bar').style.width = `${progressPct}%`;
    document.getElementById('completed-modules').textContent =
        `${overview.completed_module_count} modules completed`;

    // Activity
    const daysSinceActivity = overview.days_since_last_activity;
    document.getElementById('days-since-activity').textContent = daysSinceActivity;
    document.getElementById('activity-warning').classList.toggle('hidden', daysSinceActivity <= 7);

    // Status
    document.getElementById('current-status').textContent = overview.current_status;
    const statusIcon = document.getElementById('status-icon');
    const statusColors = {
        'Completed': { bg: 'bg-green-100', svg: 'text-green-600' },
        'Dropout': { bg: 'bg-red-100', svg: 'text-red-600' },
        'Active': { bg: 'bg-blue-100', svg: 'text-blue-600' }
    };
    
    statusIcon.className = 'flex-shrink-0 w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center';
    if (statusColors[overview.current_status]) {
        const colors = statusColors[overview.current_status];
        statusIcon.classList.remove('bg-slate-100');
        statusIcon.classList.add(colors.bg);
        statusIcon.querySelector('svg').classList.add(colors.svg);
    }

    // Timestamp
    const t = data.server_time_iso ? new Date(data.server_time_iso) : new Date();
    document.getElementById('last-updated').textContent = `Updated: ${t.toLocaleString()}`;

    // Phase 2: Load above-the-fold charts (50ms delay)
    setTimeout(() => {
        destroyCharts();
        renderEngagementTrendChart(data.engagement_trend || [], data.class_average || []);
        renderTimeAffinityChart(data.time_affinity || []);
        if (data.comparison) renderComparisonSection(data.comparison);
    }, 50);

    // Phase 3: Load tables and lists (100ms delay)
    setTimeout(() => {
        depthRowsAll = data.engagement_depth || [];
        document.getElementById('depth-filter').value = '';
        renderDepthRows(depthRowsAll);
        setSectionVisibility(data);
        renderDeadlinesSection(data.deadlines || []);
    }, 100);

    // Phase 4: Render remaining sections directly
    setTimeout(() => {
        console.log('[SD] Phase4 data keys:', Object.keys(data));
        console.log('[SD] transitions:', (data.transitions||[]).length, 'lifecycle:', JSON.stringify(data.lifecycle_milestones), 'daily:', (data.daily_activity||[]).length);
        // Force show sections trước, các render function sẽ tự hide nếu không có data
        ['transitions-section', 'lifecycle-section', 'heatmap-section', 'insights-section'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.classList.remove('hidden');
        });
        renderSankeyStudent(data.transitions || []);
        renderLifecycleSection(data.lifecycle_milestones || {}, overview);
        renderHeatmapSection(data.daily_activity || []);
        renderInsightsSection(data);
    }, 200);
}

function applyStudentData(data) {
    applyStudentDataProgressive(data);
}

// ============================================================================
// DATA FETCHING
// ============================================================================

function loadStudentData(studentKey, courseKey, isRefresh) {
    // Check cache first
    if (!isRefresh) {
        const cachedData = getCachedData(studentKey, courseKey);
        if (cachedData) {
            console.log('Using cached data');
            applyStudentData(cachedData);
            return;
        }
    } else {
        clearCache(studentKey, courseKey);
    }
    
    if (isRefresh) {
        document.getElementById('refresh-toast').classList.add('hidden');
        document.getElementById('loading-state').classList.remove('hidden');
        document.getElementById('overview-metrics').classList.add('hidden');
        ['comparison-section', 'depth-section', 'deadlines-section', 'transitions-section', 
         'lifecycle-section', 'heatmap-section', 'insights-section', 'engagement-trend-section', 
         'time-affinity-section'].forEach(id => {
            document.getElementById(id).classList.add('hidden');
        });
    }

    fetch(`?action=getdata&student_key=${encodeURIComponent(studentKey)}&course_key=${encodeURIComponent(courseKey)}`)
        .then(response => {
            if (!response.ok) throw new Error('Failed to fetch data');
            return response.json();
        })
        .then(data => {
            if (data.error) throw new Error(data.error);
            
            setCachedData(studentKey, courseKey, data);
            applyStudentData(data);
            
            if (isRefresh) {
                const toast = document.getElementById('refresh-toast');
                toast.textContent = 'Data refreshed successfully.';
                toast.classList.remove('hidden');
            }
        })
        .catch(error => {
            console.error('Error loading student data:', error);
            document.getElementById('loading-state').classList.add('hidden');
            document.getElementById('overview-metrics').classList.add('hidden');
            document.getElementById('error-state').classList.remove('hidden');
            document.getElementById('error-message').textContent = error.message;
        });
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    const studentKey = window.STUDENT_KEY;
    const courseKey = window.COURSE_KEY;

    loadStudentData(studentKey, courseKey, false);

    document.getElementById('btn-refresh-data').addEventListener('click', function() {
        loadStudentData(studentKey, courseKey, true);
    });
    
    document.getElementById('btn-export-print').addEventListener('click', function() {
        try {
            if (!window.print) {
                throw new Error('Print functionality is not supported in this browser');
            }
            window.print();
        } catch (error) {
            console.error('PDF Export Error:', error);
            
            const errorMsg = document.createElement('div');
            errorMsg.className = 'fixed top-4 right-4 z-50 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 shadow-lg max-w-md';
            errorMsg.innerHTML = `
                <div class="flex items-start gap-3">
                    <svg class="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                    <div>
                        <div class="font-bold mb-1">Export Failed</div>
                        <div class="text-sm mb-2">${error.message}</div>
                        <div class="text-xs text-red-700">
                            <strong>Suggestions:</strong>
                            <ul class="list-disc ml-4 mt-1">
                                <li>Try a different browser (Chrome, Firefox, Edge)</li>
                                <li>Check if pop-ups are blocked</li>
                                <li>Reduce date range to decrease data size</li>
                                <li>Take screenshots of individual sections</li>
                            </ul>
                        </div>
                    </div>
                    <button onclick="this.parentElement.parentElement.remove()" class="text-red-600 hover:text-red-800">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
            `;
            document.body.appendChild(errorMsg);
            setTimeout(() => { if (errorMsg.parentElement) errorMsg.remove(); }, 10000);
        }
    });
    
    document.getElementById('depth-filter').addEventListener('change', function() {
        renderDepthRows(depthRowsAll);
    });
});
