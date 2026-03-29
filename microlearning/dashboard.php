<?php
/**
 * Moodle Micro Learning Analytics Dashboard.
 * 
 * Data-Centric Version: Visualizes raw Datamart metrics without complex heuristics.
 *
 * @package     local_microlearning
 * @copyright   2024
 * @license     http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');
require_once(__DIR__ . '/lib.php');

// 1. Fetch parameters first
$courseid = optional_param('courseid', '', PARAM_RAW);
$week = optional_param('week', 'latest', PARAM_RAW);

// 2. Fetch course list from Datamart to determine default course if needed
$courses = [];
try {
    $conn = local_microlearning_get_sqlserver_connection();
    if ($conn) {
        $stmt = $conn->query("SELECT course_key, course_name FROM datamart.dim_course WHERE CAST(course_key AS VARCHAR) != '1' ORDER BY course_name ASC");
        $courses = $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
} catch (Exception $e) { }

// 3. Fallback logic for courseid
if ((empty($courseid) || $courseid === '1') && !empty($courses)) {
    $courseid = (string)$courses[0]['course_key'];
} else if (empty($courseid)) {
    $courseid = '1'; 
}

// 4. Set Moodle Context and Login
if (is_numeric($courseid) && $courseid > 1) {
    try {
        $course = $DB->get_record('course', array('id' => (int)$courseid), '*', MUST_EXIST);
        $context = context_course::instance($course->id);
        require_login($course);
    } catch (Exception $e) {
        $context = context_system::instance();
        require_login();
    }
} else {
    $context = context_system::instance();
    require_login();
}

$isteacher = has_capability('moodle/course:manageactivities', $context) || is_siteadmin();
$currentuserid = $USER->id;

// Page Setup
$PAGE->set_url(new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $courseid, 'week' => $week]));
$PAGE->set_context($context);
$PAGE->set_title('Datamart Analytics');
$PAGE->set_heading('Learning Analytics Dashboard');

// AJAX Data Handler
// AJAX Data Handler
$action = optional_param('action', '', PARAM_ALPHA);
if ($action === 'getdata') {
    header('Content-Type: application/json');
    try {
        $conn = local_microlearning_get_sqlserver_connection();
        if (!$conn)
            throw new Exception('PostgreSQL connection failed');

        $data = [];
        $viewall = optional_param('viewall', 0, PARAM_INT);
        $limit = $viewall ? 1000 : 20;

        if ($isteacher) {
            // 0. Fetch available weeks for the filter
            $stmt = $conn->prepare("
                SELECT DISTINCT year, week_of_year 
                FROM datamart.fact_risk_student_weekly 
                WHERE CAST(course_key AS VARCHAR) = ?
                ORDER BY year DESC, week_of_year DESC 
                LIMIT 20
            ");
            $stmt->execute([$courseid]);
            $data['available_weeks'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // Determine specific week filter
            $week_filter = "";
            $week_params = [$courseid];
            if ($week !== 'latest' && strpos($week, '-') !== false) {
                list($y, $w) = explode('-', $week);
                $week_filter = " AND year = ? AND week_of_year = ? ";
                $week_params[] = (int)$y;
                $week_params[] = (int)$w;
            }

            // 1. Overview Metrics (fact_risk_student_weekly)
            $sql = "SELECT 
                        COUNT(DISTINCT student_key) as total_students,
                        AVG(engagement_score) as avg_engagement,
                        AVG(risk_score) as avg_risk,
                        AVG(outcome_score) as avg_outcome
                    FROM datamart.fact_risk_student_weekly
                    WHERE CAST(course_key AS VARCHAR) = ?";

            if ($week === 'latest') {
                $sql .= " AND (year, week_of_year) IN (SELECT year, week_of_year FROM datamart.fact_risk_student_weekly WHERE CAST(course_key AS VARCHAR) = ? ORDER BY year DESC, week_of_year DESC LIMIT 1)";
                $stmt = $conn->prepare($sql);
                $stmt->execute([$courseid, $courseid]);
            }
            else if ($week === 'all') {
                $stmt = $conn->prepare($sql);
                $stmt->execute([$courseid]);
            }
            else {
                $sql .= $week_filter;
                $stmt = $conn->prepare($sql);
                $stmt->execute($week_params);
            }
            $data['global_stats'] = $stmt->fetch(PDO::FETCH_ASSOC) ?: [
                'total_students' => 0, 'avg_engagement' => 0, 'avg_risk' => 0, 'avg_outcome' => 0
            ];

            // 2. Class Trends
            $stmt = $conn->prepare("
                SELECT week_of_year, avg_engagement_score, active_student_count, medium_engagement_count, low_engagement_count, passive_student_count
                FROM datamart.fact_class_engagement_distribution
                WHERE CAST(course_key AS VARCHAR) = ?
                ORDER BY year DESC, week_of_year DESC LIMIT 12
            ");
            $stmt->execute([$courseid]);
            $data['class_trends'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);

            // 3. Student Performance List
            $sql = "SELECT a.actor_name, f.student_key, f.engagement_score, f.risk_level, f.dropout_probability_pct, l.current_progress_pct, l.last_activity_date
                    FROM (";

            if ($week === 'latest' || $week === 'all') {
                $sql .= "SELECT DISTINCT ON (student_key) student_key, course_key, engagement_score, risk_level, dropout_probability_pct, year, week_of_year
                         FROM datamart.fact_risk_student_weekly
                         WHERE CAST(course_key AS VARCHAR) = ?
                         ORDER BY student_key, year DESC, week_of_year DESC";
                $student_params = [$courseid];
            }
            else {
                $sql .= "SELECT student_key, course_key, engagement_score, risk_level, dropout_probability_pct, year, week_of_year
                         FROM datamart.fact_risk_student_weekly
                         WHERE CAST(course_key AS VARCHAR) = ? " . $week_filter;
                $student_params = $week_params;
            }

            $sql .= ") f
                    JOIN datamart.dim_actor a ON f.student_key = a.actor_id
                    LEFT JOIN datamart.fact_student_course_lifecycle l ON f.student_key = l.student_key AND CAST(f.course_key AS VARCHAR) = CAST(l.course_key AS VARCHAR)
                    ORDER BY f.dropout_probability_pct DESC LIMIT $limit";

            $stmt = $conn->prepare($sql);
            $stmt->execute($student_params);
            $data['students'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 4. Behavioral Correlations
            $stmt = $conn->prepare("
                SELECT avg_final_score, cram_student_count
                FROM datamart.fact_behavior_outcome_correlation
                WHERE CAST(course_key AS VARCHAR) = ?
                ORDER BY year DESC, week_of_year DESC LIMIT 1
            ");
            $stmt->execute([$courseid]);
            $data['correlation'] = $stmt->fetch(PDO::FETCH_ASSOC) ?: ['avg_final_score' => 0, 'cram_student_count' => 0];

            // 4.b Cramming History (Trend)
            $stmt = $conn->prepare("
                SELECT week_of_year, cram_student_count
                FROM datamart.fact_behavior_outcome_correlation
                WHERE CAST(course_key AS VARCHAR) = ?
                ORDER BY year DESC, week_of_year DESC LIMIT 12
            ");
            $stmt->execute([$courseid]);
            $data['cramming_history'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);

            // 5. Engagement Depth
            $stmt = $conn->prepare("
                SELECT engagement_type, COUNT(*) as count
                FROM datamart.fact_student_engagement_depth
                WHERE CAST(course_key AS VARCHAR) = ?
                GROUP BY engagement_type
            ");
            $stmt->execute([$courseid]);
            $data['engagement_depth'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 6. Deadline Proximity / Pressure
            $stmt = $conn->prepare("
                SELECT pressure_level, COUNT(*) as count
                FROM datamart.fact_student_deadline_proximity
                WHERE CAST(course_key AS VARCHAR) = ?
                GROUP BY pressure_level
            ");
            $stmt->execute([$courseid]);
            $data['pressure_distribution'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 7. Top Transitions
            $stmt = $conn->prepare("
                SELECT r1.resource_name as from_res, r2.resource_name as to_res, t.transition_count
                FROM datamart.fact_activity_transitions t
                JOIN datamart.dim_resource r1 ON CAST(t.from_resource_key AS VARCHAR) = CAST(r1.resource_key AS VARCHAR)
                JOIN datamart.dim_resource r2 ON CAST(t.to_resource_key AS VARCHAR) = CAST(r2.resource_key AS VARCHAR)
                WHERE CAST(t.course_key AS VARCHAR) = ?
                ORDER BY t.transition_count DESC LIMIT $limit
            ");
            $stmt->execute([$courseid]);
            $data['transitions'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 8. Coverage Funnel (Tiến trình tiếp cận)
            $total_students = (int)($data['global_stats']['total_students'] ?? 0);
            $stmt = $conn->prepare("
                SELECT s.section_name, r.resource_name AS stage, 
                       COUNT(DISTINCT d.student_key) AS interacted_count,
                       (? - COUNT(DISTINCT d.student_key)) AS uninteracted_count
                FROM datamart.fact_student_engagement_depth d
                JOIN datamart.dim_resource r ON CAST(d.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
                JOIN datamart.dim_section s ON CAST(r.section_key AS VARCHAR) = CAST(s.section_key AS VARCHAR)
                WHERE CAST(d.course_key AS VARCHAR) = ?
                GROUP BY s.section_name, r.resource_name, r.resource_key
                ORDER BY s.section_name, r.resource_key ASC
            ");
            $stmt->execute([$total_students, $courseid]);
            $data['dropoff_data'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 9. Treemap Data (Module Health)
            $stmt = $conn->prepare("
                SELECT 
                    s.section_name,
                    r.resource_name,
                    COUNT(*) as total_interactions,
                    SUM(CASE WHEN d.engagement_type = 'Stuck' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as stuck_rate,
                    SUM(CASE WHEN d.engagement_type = 'Skimming' THEN 1 ELSE 0 END) * 100.0 / COUNT(*) as skimming_rate
                FROM datamart.fact_student_engagement_depth d
                JOIN datamart.dim_resource r ON CAST(d.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
                JOIN datamart.dim_section s ON CAST(r.section_key AS VARCHAR) = CAST(s.section_key AS VARCHAR)
                WHERE CAST(d.course_key AS VARCHAR) = ?
                GROUP BY s.section_name, r.resource_name, r.resource_key
                ORDER BY s.section_name, total_interactions DESC
            ");
            $stmt->execute([$courseid]);
            $data['treemap_data'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

        } else {
            // Student View
            // 1. My Lifecycle (fact_student_course_lifecycle)
            $stmt = $conn->prepare("
                SELECT current_progress_pct, completed_module_count, current_status, days_since_last_activity, last_activity_date
                FROM datamart.fact_student_course_lifecycle
                WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
                LIMIT 1
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $data['my_lifecycle'] = $stmt->fetch(PDO::FETCH_ASSOC) ?: [
                'current_progress_pct' => 0, 'completed_module_count' => 0, 'current_status' => 'No Data', 'days_since_last_activity' => '?', 'last_activity_date' => 'N/A'
            ];

            // 2. My Engagement History (fact_daily_student_engagement)
            $daily_limit = $viewall ? 365 : 90;
            $stmt = $conn->prepare("
                SELECT t.year, t.month, t.date, t.day_of_week, 
                       AVG(f.engagement_score) as score,
                       SUM(f.total_active_minutes) as total_minutes
                FROM datamart.fact_daily_student_engagement f
                JOIN datamart.dim_time t ON f.date_key = t.time_id
                WHERE f.student_key = ? AND CAST(f.course_key AS VARCHAR) = ?
                GROUP BY t.year, t.month, t.date, t.day_of_week
                ORDER BY t.year DESC, t.month DESC, t.date DESC LIMIT $daily_limit
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $data['my_daily'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);
            $data['viewall'] = $viewall;

            // 3. My Time Affinity
            $stmt = $conn->prepare("
                SELECT time_slot, efficiency_index, total_engagement_score
                FROM datamart.fact_student_time_affinity
                WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
                ORDER BY CASE 
                    WHEN time_slot = 'Morning' THEN 1
                    WHEN time_slot = 'Afternoon' THEN 2
                    WHEN time_slot = 'Evening' THEN 3
                    WHEN time_slot = 'Night' THEN 4
                    ELSE 5 
                END
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $data['my_affinity'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 4. My Engagement Depth
            $stmt = $conn->prepare("
                SELECT r.resource_name, d.depth_ratio, d.engagement_type
                FROM datamart.fact_student_engagement_depth d
                JOIN datamart.dim_resource r ON CAST(d.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
                WHERE d.student_key = ? AND CAST(d.course_key AS VARCHAR) = ?
                ORDER BY d.depth_ratio DESC LIMIT 10
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $data['my_depth'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 5. My Deadline Proximity
            $stmt = $conn->prepare("
                SELECT r.resource_name, p.pressure_level, p.deadline_date
                FROM datamart.fact_student_deadline_proximity p
                JOIN datamart.dim_resource r ON CAST(p.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
                WHERE p.student_key = ? AND CAST(p.course_key AS VARCHAR) = ?
                ORDER BY p.deadline_date ASC LIMIT 5
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $data['my_deadlines'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];

            // 6. My Cramming Indicator
            $stmt = $conn->prepare("
                SELECT COUNT(*) as critical_deadlines
                FROM datamart.fact_student_deadline_proximity
                WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
                AND pressure_level = 'Critical'
            ");
            $stmt->execute([(string)$currentuserid, $courseid]);
            $deadlines = $stmt->fetch(PDO::FETCH_ASSOC);
            $data['is_cramming'] = ($deadlines && $deadlines['critical_deadlines'] > 0);
        }

        echo json_encode($data);
    }
    catch (Exception $e) {
        echo json_encode(['error' => $e->getMessage()]);
    }
    exit;
}

echo $OUTPUT->header();
?>

<!-- Style & Assets -->
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>
<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js"></script>

<style>
    body {
        font-family: 'Inter', sans-serif;
        background: #f8fafc;
    }

    .card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 1.5rem;
        padding: 1.5rem;
        box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05), 0 2px 4px -2px rgb(0 0 0 / 0.05);
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    }

    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgb(0 0 0 / 0.1);
    }

    .skeleton {
        background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
        background-size: 200% 100%;
        animation: skeleton-loading 1.5s infinite;
    }

    @keyframes skeleton-loading {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    .stat-val {
        font-size: 2rem;
        font-weight: 800;
        color: #0f172a;
        line-height: 1;
    }

    .stat-label {
        font-size: 0.7rem;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.075em;
        margin-bottom: 0.5rem;
    }

    .modal-backdrop {
        background: rgba(15, 23, 42, 0.6);
        backdrop-filter: blur(4px);
    }

    /* Force black borders on Treemap for clear section/module separation */
    .apexcharts-treemap-rect {
        stroke: #000 !important;
        stroke-width: 2px !important;
    }
</style>

<div class="max-w-[1600px] mx-auto p-6 space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
            <h1 class="text-3xl font-extrabold text-slate-900">Datamart <span class="text-indigo-600">Analytics</span>
            </h1>
            <p class="text-slate-500">Visualizing raw learning metrics from the data warehouse.</p>
        </div>
        <div class="flex flex-wrap items-center gap-3 bg-white p-2 rounded-2xl border border-slate-200">
            <div class="flex flex-col px-2 border-r border-slate-100">
                <span class="text-[10px] font-bold text-slate-400 uppercase">Khóa học</span>
                <select id="course-selector"
                    class="bg-transparent font-bold text-slate-700 focus:outline-none cursor-pointer">
                    <?php foreach ($courses as $c): ?>
                    <option value="<?= s($c['course_key'])?>" <?= (string)$courseid === (string)$c['course_key'] ? 'selected' : '' ?>>
                        <?= s($c['course_name'])?>
                    </option>
                    <?php endforeach; ?>
                </select>
            </div>

            <?php if ($isteacher): ?>
            <div class="flex flex-col px-2">
                <span class="text-[10px] font-bold text-slate-400 uppercase">Thời gian</span>
                <select id="week-selector"
                    class="bg-transparent font-bold text-slate-700 focus:outline-none cursor-pointer">
                    <option value="latest">Tuần mới nhất</option>
                    <option value="all">Tất cả thời gian</option>
                </select>
            </div>
            <?php
endif; ?>

            <button onclick="fetchData()"
                class="bg-indigo-600 text-white p-2 rounded-xl hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 active:scale-95 ml-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                        d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
            </button>
        </div>
    </div>

    <!-- Metrics Grid -->
    <div id="metric-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"></div>

    <!-- Dashboard Content -->
    <div id="dashboard-content" class="grid grid-cols-1 lg:grid-cols-12 gap-8"></div>
</div>

<!-- Modal Detail View -->
<div id="detail-modal" class="fixed inset-0 z-[9999] hidden flex items-center justify-center p-2 sm:p-4">
    <div class="modal-backdrop absolute inset-0 z-0" onclick="closeModal()"></div>
    <div class="bg-white rounded-[2rem] shadow-2xl w-full max-w-[95vw] h-full max-h-[95vh] flex flex-col relative z-10 overflow-hidden transform transition-all border border-slate-100">
        <div class="p-6 border-b border-slate-100 flex justify-between items-center bg-white sticky top-0 z-20">
            <h2 id="modal-title" class="text-2xl font-extrabold text-slate-800">Chi tiết dữ liệu</h2>
            <button onclick="closeModal()" class="p-2 hover:bg-slate-100 rounded-full transition-colors">
                <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>
        <div id="modal-body" class="p-4 md:p-8 overflow-y-auto flex-grow custom-scrollbar">
            <!-- Content will be injected here -->
        </div>
    </div>
</div>

<script>
    const isTeacher = <?= $isteacher ? 'true' : 'false' ?>;
    const STUDENT_DRILLDOWN_PATH = '<?php echo (new moodle_url('/local/microlearning/student_detail.php'))->out(false); ?>';
    let charts = {};

    function openStudentDrilldown(studentKey) {
        const courseId = document.getElementById('course-selector').value;
        const url = STUDENT_DRILLDOWN_PATH + 
                    '?student_key=' + encodeURIComponent(studentKey) + 
                    '&course_key=' + encodeURIComponent(courseId);
        console.log('Navigating to:', url); // Debug log
        window.location.href = url;
    }

    async function fetchData() {
        const grid = document.getElementById('metric-grid');
        const content = document.getElementById('dashboard-content');
        
        // Show Skeletons
        grid.innerHTML = Array(4).fill(0).map(() => `
            <div class="card p-6 flex flex-col gap-4">
                <div class="w-12 h-12 rounded-2xl skeleton"></div>
                <div class="space-y-2">
                    <div class="w-24 h-4 skeleton rounded"></div>
                    <div class="w-16 h-8 skeleton rounded-lg"></div>
                </div>
            </div>
        `).join('');

        const courseId = document.getElementById('course-selector').value;
        const weekSelector = document.getElementById('week-selector');
        const week = weekSelector ? weekSelector.value : 'latest';

        try {
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&week=${week}`);
            const data = await resp.json();
            if (data.error) throw new Error(data.error);

            // Update week selector if we are a teacher and received weeks
            if (isTeacher && data.available_weeks) {
                const currentVal = weekSelector.value;
                let options = '<option value="latest" ' + (currentVal === 'latest' ? 'selected' : '') + '>Tuần mới nhất</option>';
                options += '<option value="all" ' + (currentVal === 'all' ? 'selected' : '') + '>Tất cả thời gian</option>';
                data.available_weeks.forEach(w => {
                    const val = `${w.year}-${w.week_of_year}`;
                    const selected = val === currentVal ? 'selected' : '';
                    options += `<option value="${val}" ${selected}>Tuần ${w.week_of_year}, ${w.year}</option>`;
                });
                weekSelector.innerHTML = options;
            }

            renderMetrics(data);
            if (isTeacher) renderTeacher(data); else renderStudent(data);
        } catch (err) {
            grid.innerHTML = `<div class="col-span-full p-12 text-center text-red-500 font-bold bg-red-50 rounded-3xl border border-red-100 italic">⚠️ Lỗi tải dữ liệu: ${err.message}</div>`;
        }
    }

    function renderMetrics(data) {
        const grid = document.getElementById('metric-grid');
        grid.innerHTML = '';
        if (!data) return;

        let metrics = [];
        if (isTeacher && data.global_stats) {
            metrics = [
                {
                    label: 'Tổng số học sinh',
                    val: data.global_stats.total_students,
                    sub: 'Người dùng định danh',
                    icon: `<svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/></svg>`,
                    color: 'bg-indigo-50',
                    tip: 'Tổng số học viên duy nhất tham gia. Giúp xác định quy mô lớp học để điều chỉnh giáo trình và khối lượng hỗ trợ phù hợp.'
                },
                {
                    label: 'Điểm tương tác TB',
                    val: Math.round(data.global_stats.avg_engagement),
                    sub: 'Điểm trung bình tuần',
                    icon: `<svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`,
                    color: 'bg-emerald-50',
                    tip: 'Cách tính (max 100đ): Tương tác tài liệu (tối đa 50đ) + Hoàn thành bài tập/Quiz (50đ). Chỉ số này phản ánh độ nhiệt huyết của lớp; mức lý tưởng là >50đ.'
                },
                {
                    label: 'Điểm rủi ro TB',
                    val: Math.round(data.global_stats.avg_risk),
                    sub: 'Chỉ số dự báo',
                    icon: `<svg class="w-6 h-6 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>`,
                    color: 'bg-rose-50',
                    tip: 'Xác suất bỏ học dự báo (0-100%). Được tính toán dựa trên sự sụt giảm tần suất đăng nhập và tiến độ làm bài. >50% cần can thiệp ngay.'
                },
                {
                    label: 'Học dồn cuối kỳ',
                    val: data.correlation?.cram_student_count || 0,
                    sub: 'SV có hành vi học dồn',
                    icon: `<svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                    color: 'bg-amber-50',
                    tip: 'Số SV có hành vi học dồn (Cramming): Học rất ít ở đầu kỳ nhưng tăng đột biến >300% thời gian ở cuối kỳ. Đây là nhóm học để đối phó, kiến thức khó bền vững.'
                }
            ];
        } else if (data.my_lifecycle) {
            metrics = [
                {
                    label: 'Tiến độ của tôi',
                    val: (data.my_lifecycle.current_progress_pct || 0) + '%',
                    sub: (data.my_lifecycle.completed_module_count || 0) + ' học phần',
                    icon: `<svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                    color: 'bg-indigo-50',
                    tip: 'Phần trăm bài học đã hoàn thành. Hệ thống tính dựa trên số lượng module/hoạt động. Bạn nên duy trì mức >10%/tuần để về đích đúng hạn.'
                },
                {
                    label: 'Trạng thái hiện tại',
                    val: data.my_lifecycle.current_status || 'N/A',
                    sub: 'Vòng đời học tập',
                    icon: `<svg class="w-6 h-6 text-sky-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/></svg>`,
                    color: 'bg-sky-50',
                    tip: 'Xếp loại dựa trên sự chuyên cần. Tích cực (học đều), Chậm trễ (vắng học > 3 ngày), Rủi ro (vắng học > 7 ngày).'
                },
                {
                    label: 'Hoạt động cuối',
                    val: (data.my_lifecycle.days_since_last_activity || 0) + ' ngày trước',
                    sub: data.my_lifecycle.last_activity_date || 'N/A',
                    icon: `<svg class="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>`,
                    color: 'bg-emerald-50',
                    tip: 'Thời điểm gần nhất bạn vào học. Duy trì khoảng cách vắng học dưới 48h để giữ thói quen học tập tốt nhất.'
                },
                {
                    label: 'Tương tác',
                    val: Math.round(data.my_daily && data.my_daily.length > 0 ? data.my_daily[data.my_daily.length - 1].score : 0),
                    sub: 'Điểm: ' + Math.round(data.my_daily && data.my_daily.length > 0 ? data.my_daily[data.my_daily.length - 1].score : 0) + ' • ' + (data.my_daily && data.my_daily.length > 0 ? Math.round(data.my_daily[data.my_daily.length - 1].total_minutes) : 0) + ' phút',
                    icon: `<svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>`,
                    color: 'bg-amber-50',
                    tip: 'Điểm nỗ lực cá nhân trong ngày gần nhất kèm theo tổng số phút học thực tế. Mục tiêu đạt trên 50đ mỗi ngày học giúp bạn ghi nhớ kiến thức lâu hơn.'
                }
            ];
        }

        metrics.forEach(m => {
            grid.innerHTML += `
                <div class="card relative group overflow-hidden">
                    <div class="flex items-start justify-between">
                        <div>
                            <div class="stat-label">${m.label}</div>
                            <div class="stat-val">${m.val}</div>
                            <div class="text-[10px] font-bold text-slate-400 mt-2 uppercase tracking-tight">${m.sub}</div>
                        </div>
                        <div class="p-3 ${m.color} rounded-2xl transition-all group-hover:scale-110">
                            ${m.icon}
                        </div>
                    </div>
                    ${m.tip ? `
                        <div class="absolute bottom-4 right-4 cursor-help opacity-40 group-hover:opacity-100 transition-opacity" title="${m.tip}">
                            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

    // Helper to safely init charts
    function safeInitChart(selector, config) {
        const el = document.querySelector(selector);
        if (!el) return null;
        try {
            const chart = new ApexCharts(el, config);
            chart.render();
            return chart;
        } catch (e) {
            console.error("Chart Error (" + selector + "):", e);
            el.innerHTML = '<div class="flex items-center justify-center h-full text-slate-400 text-xs italic">Lỗi hiển thị biểu đồ</div>';
            return null;
        }
    }

    function renderTeacher(data) {
        const content = document.getElementById('dashboard-content');
        if (!data) return;

        content.innerHTML = `
            <div class="lg:col-span-8 space-y-8">
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="card md:col-span-2">
                        <div class="flex items-center justify-between mb-6">
                            <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">Sức khỏe Module (Treemap)</h3>
                            <button onclick="viewTreemapDetail()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
                        </div>
                        <div id="module-health-treemap" class="min-h-[400px]"></div>
                        <div class="flex flex-wrap gap-4 mt-4 text-[10px] font-bold uppercase">
                            <span class="flex items-center gap-1.5 text-red-600"><span class="w-3 h-3 bg-red-500 rounded-sm"></span> Cần can thiệp (Stuck > 30%)</span>
                            <span class="flex items-center gap-1.5 text-amber-600"><span class="w-3 h-3 bg-amber-500 rounded-sm"></span> Học hời hợt (Skimming > 50%)</span>
                            <span class="flex items-center gap-1.5 text-emerald-600"><span class="w-3 h-3 bg-emerald-500 rounded-sm"></span> Học sâu (Deep Dive)</span>
                        </div>
                    </div>

                    <div class="card md:col-span-2">
                        <div class="flex items-center justify-between mb-6">
                            <h3 class="text-lg font-bold text-slate-800 flex items-center gap-2">Luồng học tập (Sankey Flow)</h3>
                            <button onclick="viewMatrixDetail()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
                        </div>
                        <div id="learning-flow" class="w-full min-h-[400px]"></div>
                        <p class="text-[10px] text-slate-400 mt-4 font-medium italic">💡 Gợi ý: Các đường nối giữa các module thể hiện hành vi chuyển tiếp của học sinh.</p>
                    </div>

                    <div class="card md:col-span-2">
                        <h3 class="text-lg font-bold mb-6 text-slate-800">Các bước chuyển tiếp phổ biến</h3>
                        <div id="top-transitions-chart"></div>
                    </div>

                    <div class="card md:col-span-2">
                        <div class="flex items-center justify-between mb-6">
                            <h3 class="text-lg font-bold mb-6 text-slate-800">Tiến trình tiếp cận học phần (Coverage Funnel)</h3>
                            <button onclick="viewCoverageDetail()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
                        </div>
                        <div id="dropoff-funnel" class="min-h-[400px]"></div>
                    </div>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="card">
                        <h3 class="text-lg font-bold mb-6 text-slate-800">Độ sâu tương tác</h3>
                        <div id="depth-chart"></div>
                    </div>
                    <div class="card">
                        <h3 class="text-lg font-bold mb-6 text-slate-800">Xu hướng tương tác lớp</h3>
                        <div id="trend-chart" class="h-[300px]"></div>
                    </div>
                </div>
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800">Xu hướng Học dồn</h3>
                    <div id="cram-chart" class="h-[300px]"></div>
                </div>
                <div class="card overflow-hidden">
                    <div class="flex items-center justify-between mb-6">
                        <h3 class="text-lg font-bold text-slate-800">Chi tiết hiệu suất sinh viên</h3>
                        <button onclick="viewStudentDetail()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Toàn bộ danh sách</button>
                    </div>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left">
                            <thead>
                                <tr class="text-[10px] font-bold text-slate-400 border-b border-slate-100 uppercase">
                                    <th class="pb-4">Sinh viên</th>
                                    <th class="pb-4">Tiến độ</th>
                                    <th class="pb-4">Rủi ro %</th>
                                    <th class="pb-4">T.Tác</th>
                                    <th class="pb-4 text-right">H.Động cuối</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-50">
                                ${data.students && data.students.length > 0 ? data.students.map(s => `
                                    <tr class="text-sm cursor-pointer hover:bg-indigo-50/60 transition-colors" onclick="openStudentDrilldown('${s.student_key}')" title="Xem chi tiết sinh viên">
                                        <td class="py-4 font-bold text-slate-700">${s.actor_name || s.student_key}</td>
                                        <td class="py-4">
                                            <div class="flex items-center gap-2">
                                                <div class="w-16 h-1 bg-slate-100 rounded-full overflow-hidden">
                                                    <div class="h-full bg-indigo-500" style="width:${s.current_progress_pct}%"></div>
                                                </div>
                                                <span class="text-[10px] font-bold text-slate-400">${s.current_progress_pct}%</span>
                                            </div>
                                        </td>
                                        <td class="py-4 font-bold ${s.dropout_probability_pct > 50 ? 'text-red-500' : 'text-slate-600'}">${Math.round(s.dropout_probability_pct)}%</td>
                                        <td class="py-4 font-mono text-xs text-slate-500 font-bold">${s.engagement_score}</td>
                                        <td class="py-4 text-right text-[10px] font-bold text-slate-400">${s.last_activity_date}</td>
                                    </tr>
                                `).join('') : '<tr><td colspan="5" class="py-12 text-center text-slate-400 italic">Chưa có dữ liệu sinh viên</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="lg:col-span-4 space-y-8">
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800">Phân loại tương tác</h3>
                    <div id="mix-chart"></div>
                </div>
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800">Phân bổ Áp lực Deadline</h3>
                    <div id="pressure-chart"></div>
                </div>
                <div class="card border-indigo-100 border-l-4 border-l-indigo-600">
                    <h3 class="text-lg font-bold mb-4 text-indigo-900">Mối tương quan hành vi</h3>
                    <div class="space-y-4 text-sm">
                        <div class="flex justify-between items-center">
                            <div class="text-[10px] font-black uppercase text-slate-400">Điểm số TB</div>
                            <div class="text-2xl font-black text-indigo-600">${data.correlation?.avg_final_score || 0}%</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Wait a tick for DOM to update
        setTimeout(() => {
            if (data.treemap_data && data.treemap_data.length > 0) {
                renderTreemapOverview(data.treemap_data);
            }

            if (data.transitions && data.transitions.length > 0) {
                renderSankeyOverview(data.transitions);
                renderTopTransitionsOverview(data.transitions);
            }

            if (data.dropoff_data && data.dropoff_data.length > 0) {
                renderCoverageOverview(data.dropoff_data);
            }

            safeInitChart("#trend-chart", {
                series: [{ name: 'Điểm tương tác TB', data: (data.class_trends || []).map(t => t.avg_engagement_score) }],
                chart: { type: 'area', height: 300, toolbar: { show: false } },
                stroke: { curve: 'smooth', width: 3 },
                xaxis: { categories: (data.class_trends || []).map(t => 'T' + t.week_of_year) },
                colors: ['#6366f1']
            });

            safeInitChart("#depth-chart", {
                series: (data.engagement_depth || []).map(d => parseInt(d.count)),
                chart: { type: 'donut', height: 250 },
                labels: (data.engagement_depth || []).map(d => d.engagement_type),
                colors: ['#10b981', '#f59e0b', '#ef4444'],
                legend: { position: 'bottom' }
            });

            safeInitChart("#cram-chart", {
                series: [{ name: 'SV Học dồn', data: (data.cramming_history || []).map(t => t.cram_student_count) }],
                chart: { type: 'area', height: 300, toolbar: { show: false } },
                stroke: { curve: 'smooth', width: 3 },
                xaxis: { categories: (data.cramming_history || []).map(t => 'T' + t.week_of_year) },
                colors: ['#f43f5e']
            });

            safeInitChart("#pressure-chart", {
                series: (data.pressure_distribution || []).map(d => parseInt(d.count)),
                chart: { type: 'pie', height: 250 },
                labels: (data.pressure_distribution || []).map(d => d.pressure_level),
                colors: ['#10b981', '#f59e0b', '#ef4444'],
                legend: { position: 'bottom' }
            });

            safeInitChart("#mix-chart", {
                series: (data.class_trends && data.class_trends.length > 0) ? [
                    data.class_trends[data.class_trends.length - 1].active_student_count || 0,
                    data.class_trends[data.class_trends.length - 1].medium_engagement_count || 0,
                    data.class_trends[data.class_trends.length - 1].low_engagement_count || 0,
                    data.class_trends[data.class_trends.length - 1].passive_student_count || 0
                ] : [0, 0, 0, 0],
                chart: { type: 'donut', height: 280 },
                labels: ['Tích cực', 'Trung bình', 'Thấp', 'Thụ động'],
                colors: ['#6366f1', '#8b5cf6', '#f43f5e', '#e2e8f0'],
                legend: { position: 'bottom' }
            });
        }, 50);
    }

    function renderStudent(data) {
        const content = document.getElementById('dashboard-content');
        if (!data) return;

        if (!data.my_daily || data.my_daily.length === 0) {
            content.innerHTML = `
                <div class="col-span-full py-20 text-center bg-white rounded-[2rem] border border-slate-100 shadow-sm">
                    <div class="p-4 bg-slate-50 w-20 h-20 rounded-full mx-auto mb-6 flex items-center justify-center">
                        <svg class="w-10 h-10 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </div>
                    <h3 class="text-xl font-bold text-slate-800 mb-2">Chưa có dữ liệu học tập</h3>
                    <p class="text-slate-500 max-w-sm mx-auto">Hệ thống chưa ghi nhận hoạt động của bạn trong khóa học này. Hãy bắt đầu học để xem số liệu phân tích!</p>
                </div>
            `;
            return;
        }

        content.innerHTML = `
            <div class="lg:col-span-8 space-y-8">
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">Lịch sử tương tác của tôi</h3>
                    <div id="engagement-chart" class="h-[350px]"></div>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div class="card">
                        <h3 class="text-lg font-bold mb-6 text-slate-800">Nhịp sinh học học tập</h3>
                        <div id="affinity-chart" class="min-h-[250px]"></div>
                        <p class="text-[10px] text-slate-400 mt-4 font-medium italic text-center">💡 Gợi ý: Khung giờ có đỉnh cao nhất là lúc bạn tập trung tốt nhất.</p>
                    </div>
                    <div class="card">
                        <h3 class="text-lg font-bold mb-6 text-slate-800">Áp lực Deadline</h3>
                        <div class="space-y-4">
                            ${(data.my_deadlines && data.my_deadlines.length > 0) ? data.my_deadlines.map(d => `
                                <div class="p-3 rounded-xl border-l-4 ${d.pressure_level === 'Critical' ? 'bg-red-50 border-red-500' : (d.pressure_level === 'Warning' ? 'bg-amber-50 border-amber-500' : 'bg-green-50 border-green-500')}">
                                    <div class="text-xs font-bold text-slate-700 truncate">${d.resource_name}</div>
                                    <div class="flex justify-between items-center mt-1">
                                        <span class="text-[10px] font-bold uppercase ${d.pressure_level === 'Critical' ? 'text-red-600' : (d.pressure_level === 'Warning' ? 'text-amber-600' : 'text-green-600')}">${d.pressure_level}</span>
                                    </div>
                                </div>
                            `).join('') : '<div class="text-center text-slate-400 text-sm italic py-8">Không có dữ liệu deadline</div>'}
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800">Độ sâu học tập</h3>
                    <div id="depth-chart" class="min-h-[300px]"></div>
                </div>
            </div>
            <div class="lg:col-span-4 flex flex-col gap-6 h-full">
                <div class="card border-indigo-50 shadow-sm p-4 min-h-[300px]">
                    <h3 class="text-sm font-semibold mb-4 text-slate-800 flex items-center gap-2">Lịch sử hoạt động (90 ngày)</h3>
                    <div id="activity-heatmap" class="w-full h-[220px] flex items-center justify-center overflow-x-auto scrollbar-hide"></div>
                </div>

                <div class="card p-4">
                    <div class="flex items-center justify-between mb-4">
                        <h3 class="text-sm font-semibold text-slate-800">Nhật ký hoạt động</h3>
                        <button onclick="viewActivityDetail()" class="text-[9px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest">Chi tiết</button>
                    </div>
                    <div class="space-y-2">
                        ${data.my_daily.slice(-8).reverse().map(d => `
                            <div class="flex items-center justify-between px-3 py-2.5 bg-slate-50 rounded-lg border border-slate-100">
                                <div>
                                    <div class="text-xs font-semibold text-slate-700">${d.day_of_week}, ${d.date}</div>
                                    <div class="text-[11px] text-slate-400">
                                        Điểm: <span class="font-semibold">${Math.round(d.score)}</span> 
                                        • Phút: <span class="font-semibold text-indigo-600">${Math.round(d.total_minutes || 0)}</span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>

                <div class="card border-indigo-100 border-l-4 border-l-indigo-600 p-4 flex-grow">
                    <h3 class="text-sm font-semibold mb-3 text-indigo-900">Insight hành vi</h3>
                    <div class="text-xs space-y-3 text-slate-600 leading-relaxed font-medium">
                        ${(() => {
                            const best = data.my_affinity && data.my_affinity.length > 0 ? [...data.my_affinity].sort((a, b) => parseFloat(b.efficiency_index) - parseFloat(a.efficiency_index))[0] : null;
                            return best ? `<div class="p-3 bg-indigo-50/60 rounded-lg border border-indigo-100">🌟 Hiệu suất cao nhất vào <b class="text-indigo-700">${best.time_slot}</b>.</div>` : '';
                        })()}
                        ${(() => {
                            const skim = data.my_depth ? data.my_depth.find(d => d.engagement_type === 'Skimming') : null;
                            return skim ? `<div class="p-3 bg-amber-50 rounded-lg border border-amber-100">⚠️ Đang học lướt qua <b class="text-amber-700">${skim.resource_name.substring(0, 30)}...</b>.</div>` : '';
                        })()}
                        ${data.is_cramming ? `<div class="p-4 bg-rose-50 rounded-2xl border-2 border-rose-200 animate-pulse text-rose-800 font-bold">🚨 Cảnh báo Học dồn! Hãy chia nhỏ thời gian học.</div>` : `<div class="p-3 bg-emerald-50 rounded-lg border border-emerald-100 text-emerald-700">✅ Nhịp độ học tập đang ổn định.</div>`}
                    </div>
                </div>
            </div>
        `;

        // Render Charts safely after DOM update
        setTimeout(() => {
            safeInitChart("#engagement-chart", {
                series: [{ name: 'Điểm tương tác', data: (data.my_daily || []).map(d => Math.round(d.score)) }],
                chart: { type: 'area', height: 350, toolbar: { show: false } },
                stroke: { curve: 'smooth' },
                xaxis: { categories: (data.my_daily || []).map(d => d.date) },
                colors: ['#6366f1']
            });

            if (data.my_affinity && data.my_affinity.length > 0) {
                safeInitChart("#affinity-chart", {
                    series: [{ name: 'Chỉ số hiệu suất', data: data.my_affinity.map(a => parseFloat(a.efficiency_index)) }],
                    chart: { type: data.my_affinity.length > 2 ? 'radar' : 'bar', height: 300, toolbar: { show: false } },
                    xaxis: { categories: data.my_affinity.map(a => a.time_slot) },
                    colors: ['#8b5cf6'],
                    fill: { opacity: 0.4 },
                    yaxis: { show: false }
                });
            }

            if (data.my_depth && data.my_depth.length > 0) {
                safeInitChart("#depth-chart", {
                    series: [{ name: 'Tỷ lệ chiều sâu', data: data.my_depth.map(d => d.depth_ratio) }],
                    chart: { type: 'bar', height: 300, toolbar: { show: false } },
                    plotOptions: { bar: { distributed: true, borderRadius: 8 } },
                    xaxis: {
                        categories: data.my_depth.map(d => (d.resource_name || '...').substring(0, 15) + '...'),
                        labels: { style: { fontSize: '10px' } }
                    },
                    colors: data.my_depth.map(d => d.engagement_type === 'Skimming' ? '#f43f5e' : (d.engagement_type === 'Stuck' ? '#fbbf24' : '#10b981')),
                    legend: { show: false }
                });
            }

            if (data.my_daily && data.my_daily.length > 0) {
                renderActivityGrid(data.my_daily);
            } else {
                const hm = document.getElementById('activity-heatmap');
                if (hm) hm.innerHTML = '<div class="text-center text-slate-400 py-8 italic text-sm">Chưa có dữ liệu hoạt động</div>';
            }
        }, 50);
    }


    function renderActivityGrid(dailyData) {

        const container = document.getElementById('activity-heatmap');
        container.innerHTML = '';

        const dataMap = {};
        dailyData.forEach(d => {
            const key = `${d.year}-${d.month}-${d.date}`;
            dataMap[key] = d;
        });

        const now = new Date();

        // lấy 3 tháng gần nhất
        const months = [];
        for (let i = 2; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
            months.push({
                year: d.getFullYear(),
                month: d.getMonth()
            });
        }

        const cellSize = 14;
        const cellGap = 4;
        const rows = 7;
        const monthWidth = 120;

        const svg = d3.select("#activity-heatmap")
            .append("svg")
            .attr("width", "100%")
            .attr("height", 240)
            .attr("viewBox", "0 0 420 240")
            .attr("preserveAspectRatio", "xMinYMid meet");

        const colorScale = d3.scaleThreshold()
            .domain([1, 20, 45, 75])
            .range(["#475569", "#9be9a8", "#40c463", "#30a14e", "#216e39"]);

        const dayNames = ['CN', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7'];

        // Day labels
        const daysG = svg.append("g").attr("transform", "translate(5,40)");
        [1, 3, 5].forEach(idx => {
            daysG.append("text")
                .attr("x", 0)
                .attr("y", idx * (cellSize + cellGap) + cellSize - 2)
                .attr("font-size", "11px")
                .attr("font-weight", "bold")
                .attr("fill", "#64748b")
                .text(dayNames[idx]);
        });

        const gridG = svg.append("g").attr("transform", "translate(35,40)");

        months.forEach((m, monthIndex) => {

            const firstDay = new Date(m.year, m.month, 1);
            const lastDay = new Date(m.year, m.month + 1, 0);
            const daysInMonth = lastDay.getDate();

            const startOffset = firstDay.getDay();

            // month label
            gridG.append("text")
                .attr("x", monthIndex * monthWidth)
                .attr("y", -12)
                .attr("font-size", "13px")
                .attr("font-weight", "bold")
                .attr("fill", "#1e293b")
                .text(`Tháng ${m.month + 1}`);

            for (let d = 1; d <= daysInMonth; d++) {

                const date = new Date(m.year, m.month, d);
                const index = startOffset + d - 1;

                const col = Math.floor(index / rows);
                const row = index % rows;

                const key = `${m.year}-${m.month + 1}-${d}`;
                const data = dataMap[key];
                const score = data ? parseFloat(data.score || 0) : 0;
                const minutes = data ? parseFloat(data.total_minutes || 0) : 0;

                const fillColor = (data && score > 0)
                    ? colorScale(score)
                    : "#759599ce"; // xám đậm cho ngày không có dữ liệu

                gridG.append("rect")
                    .attr("width", cellSize)
                    .attr("height", cellSize)
                    .attr("x", monthIndex * monthWidth + col * (cellSize + cellGap))
                    .attr("y", row * (cellSize + cellGap))
                    .attr("rx", 3)
                    .attr("fill", fillColor)
                    .append("title")
                    .text(data
                        ? `${d}/${m.month + 1}/${m.year}: ${Math.round(score)}đ / ${Math.round(minutes)} phút`
                        : `${d}/${m.month + 1}/${m.year}: Không có hoạt động`);
            }
        });

        // legend
        const legend = svg.append("g").attr("transform", "translate(35,190)");

        const colors = ["#759599ce", "#9be9a8", "#40c463", "#30a14e", "#216e39"];

        colors.forEach((color, i) => {
            legend.append("rect")
                .attr("x", i * 22)
                .attr("width", 14)
                .attr("height", 14)
                .attr("fill", color)
                .attr("rx", 3);
        });

        legend.append("text")
            .attr("x", -22)
            .attr("y", 11)
            .attr("font-size", "11px")
            .attr("fill", "#94a3b8")
            .text("Ít");

        legend.append("text")
            .attr("x", colors.length * 22 + 4)
            .attr("y", 11)
            .attr("font-size", "11px")
            .attr("fill", "#94a3b8")
            .text("Nhiều");

    }

    function renderTreemap(data) {
        // Group data by section
        const grouped = {};
        data.forEach(d => {
            if (!grouped[d.section_name]) grouped[d.section_name] = [];
            
            let color = '#10b981'; // Green
            if (parseFloat(d.stuck_rate) > 30) color = '#ef4444'; // Red
            else if (parseFloat(d.skimming_rate) > 50) color = '#f59e0b'; // Amber
            
            grouped[d.section_name].push({
                x: d.resource_name,
                y: parseInt(d.total_interactions),
                fillColor: color,
                stuck: Math.round(d.stuck_rate),
                skim: Math.round(d.skimming_rate)
            });
        });

        const series = Object.keys(grouped).map(section => ({
            name: section,
            data: grouped[section]
        }));

        safeInitChart("#module-health-treemap", {
            series: series,
            legend: { show: false },
            chart: {
                height: 450,
                type: 'treemap',
                toolbar: { show: false }
            },
            plotOptions: {
                treemap: {
                    distributed: true,
                    enableShades: false
                }
            },
            dataLabels: {
                enabled: true,
                style: { fontSize: '11px' },
                formatter: (text, op) => [text, op.value + ' nỗ lực']
            },
            tooltip: {
                y: {
                    formatter: (val, { seriesIndex, dataPointIndex, w }) => {
                        const item = w.config.series[seriesIndex].data[dataPointIndex];
                        return `${val} tương tác | Stuck: ${item.stuck}% | Skimming: ${item.skim}%`;
                    }
                }
            }
        });
    }

    function renderTreemapOverview(data) {
        // Aggregate data by section for high-level view
        const sectionAgg = {};
        data.forEach(d => {
            if (!sectionAgg[d.section_name]) {
                sectionAgg[d.section_name] = { interactions: 0, stuck_sum: 0, count: 0 };
            }
            sectionAgg[d.section_name].interactions += parseInt(d.total_interactions);
            sectionAgg[d.section_name].stuck_sum += parseFloat(d.stuck_rate);
            sectionAgg[d.section_name].count += 1;
        });

        const seriesData = Object.keys(sectionAgg).map(name => {
            const avgStuck = sectionAgg[name].stuck_sum / sectionAgg[name].count;
            let color = '#10b981';
            if (avgStuck > 30) color = '#ef4444';
            else if (avgStuck > 15) color = '#f59e0b';

            return { x: name, y: sectionAgg[name].interactions, fillColor: color };
        });

        safeInitChart("#module-health-treemap", {
            series: [{ data: seriesData }],
            chart: { height: 350, type: 'treemap', toolbar: { show: false } },
            stroke: { show: true, width: 4, colors: ['#000'] },
            plotOptions: { treemap: { distributed: true, enableShades: false } },
            dataLabels: { enabled: true, formatter: (text) => text }
        });
    }

    async function viewTreemapDetail() {
        showModal('Phân tích chi tiết Sức khỏe Module theo Chương', `
            <div id="modal-treemap-container" class="grid grid-cols-1 md:grid-cols-2 gap-8">
                <!-- Các khối Section sẽ được render vào đây -->
            </div>
        `);

        try {
            const courseId = document.getElementById('course-selector').value;
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&viewall=1`);
            const data = await resp.json();

            const container = document.getElementById('modal-treemap-container');
            container.innerHTML = '';

            const grouped = {};
            data.treemap_data.forEach(d => {
                if (!grouped[d.section_name]) grouped[d.section_name] = [];
                let color = '#10b981';
                if (parseFloat(d.stuck_rate) > 30) color = '#ef4444';
                else if (parseFloat(d.skimming_rate) > 15) color = '#f59e0b';

                grouped[d.section_name].push({
                    x: d.resource_name,
                    y: parseInt(d.total_interactions),
                    fillColor: color,
                    stuck: Math.round(d.stuck_rate),
                    skim: Math.round(d.skimming_rate)
                });
            });

            Object.keys(grouped).forEach((sectionName, index) => {
                const sectionId = `modal-section-chart-${index}`;
                container.innerHTML += `
                    <div class="flex flex-col border-[4px] border-black rounded-lg overflow-hidden bg-white shadow-[8px_8px_0px_0px_rgba(0,0,0,1)] hover:translate-x-[-3px] hover:translate-y-[-3px] hover:shadow-[11px_11px_0px_0px_rgba(0,0,0,1)] transition-all duration-150">
                        <div class="bg-black text-white px-6 py-3 font-black uppercase tracking-widest text-sm">
                            ${sectionName}
                        </div>
                        <div class="p-4 bg-white">
                            <div id="${sectionId}" class="min-h-[350px]"></div>
                        </div>
                    </div>
                `;

                setTimeout(() => {
                    new ApexCharts(document.querySelector(`#${sectionId}`), {
                        series: [{ data: grouped[sectionName] }],
                        chart: { height: 350, type: 'treemap', toolbar: { show: false } },
                        stroke: { show: true, width: 1, colors: ['#ffffffaa'] },
                        plotOptions: { 
                            treemap: { 
                                distributed: true, 
                                enableShades: false,
                                useFillColorAsStroke: false 
                            } 
                        },
                        dataLabels: { enabled: true, style: { fontSize: '11px', fontWeight: 600 } },
                        tooltip: {
                            y: {
                                formatter: (val, { seriesIndex, dataPointIndex, w }) => {
                                    const item = w.config.series[0].data[dataPointIndex];
                                    return `${val} lượt | Stuck: ${item.stuck}% | Skimming: ${item.skim}%`;
                                }
                            }
                        }
                    }).render();
                }, 10);
            });
        } catch (err) { console.error(err); }
    }

    function renderCoverageOverview(data) {
        // Aggregate coverage by section
        const sectionAgg = {};
        data.forEach(d => {
            if (!sectionAgg[d.section_name]) {
                sectionAgg[d.section_name] = { interacted: 0, total: 0, count: 0 };
            }
            const total = parseInt(d.interacted_count) + parseInt(d.uninteracted_count);
            sectionAgg[d.section_name].interacted += parseInt(d.interacted_count);
            sectionAgg[d.section_name].total += total;
            sectionAgg[d.section_name].count += 1;
        });

        const categories = Object.keys(sectionAgg);
        const seriesData = categories.map(name => {
            const item = sectionAgg[name];
            return item.total > 0 ? Math.round((item.interacted / item.total) * 100) : 0;
        });

        safeInitChart("#dropoff-funnel", {
            series: [{ name: 'Độ bao phủ (%)', data: seriesData }],
            chart: { type: 'bar', height: 300, toolbar: { show: false } },
            plotOptions: { bar: { horizontal: true, borderRadius: 8, barHeight: '50%' } },
            colors: ['#6366f1'],
            xaxis: { categories: categories, max: 100 },
            dataLabels: { enabled: true, formatter: (val) => val + '%' }
        });
    }

    function renderSankeyOverview(linksRaw) {
        // A very simplified Sankey or just a placeholder for the main one
        renderSankey(linksRaw, "#learning-flow", 350);
    }

    function renderTopTransitionsOverview(links) {
        const top3 = [...links].sort((a, b) => b.transition_count - a.transition_count).slice(0, 3);
        safeInitChart("#top-transitions-chart", {
            series: [{ name: 'Transitions', data: top3.map(d => d.transition_count) }],
            chart: { type: 'bar', height: 200, toolbar: { show: false } },
            plotOptions: { bar: { horizontal: true, borderRadius: 4 } },
            xaxis: { categories: top3.map(d => `${d.from_res.substring(0, 10)}... → ${d.to_res.substring(0, 10)}...`) },
            colors: ['#8b5cf6']
        });
    }

    function renderSankey(linksRaw, selector = "#learning-flow", height = 400) {
        const container = document.querySelector(selector);
        if (!container) return;
        container.innerHTML = '';
        const width = container.offsetWidth || 800;
        
        const svg = d3.select(selector).append("svg")
            .attr("width", "100%").attr("height", height)
            .attr("viewBox", `0 0 ${width} ${height}`);

        const sankey = d3.sankey()
            .nodeWidth(15)
            .nodePadding(15)
            .extent([[1, 1], [width - 1, height - 6]]);

        const nodes = Array.from(new Set([...linksRaw.map(d => d.from_res), ...linksRaw.map(d => d.to_res)]))
            .map(name => ({ name }));
        const nodeMap = new Map(nodes.map((d, i) => [d.name, i]));
        
        const processedLinks = [];
        linksRaw.forEach(d => {
            const s = nodeMap.get(d.from_res), t = nodeMap.get(d.to_res);
            if (s !== undefined && t !== undefined && s < t) {
                processedLinks.push({ source: s, target: t, value: Math.max(1, parseInt(d.transition_count)) });
            }
        });

        if (processedLinks.length === 0) {
            container.innerHTML = '<div class="flex items-center justify-center h-full text-slate-400 italic text-xs">Không đủ dữ liệu luồng tuyến tính</div>';
            return;
        }

        const graph = sankey({ 
            nodes: nodes.map(d => Object.assign({}, d)), 
            links: processedLinks.map(d => Object.assign({}, d)) 
        });

        const color = d3.scaleOrdinal(d3.schemeCategory10);

        // Links
        svg.append("g")
            .attr("fill", "none")
            .attr("stroke-opacity", 0.3)
            .selectAll("path")
            .data(graph.links)
            .join("path")
            .attr("d", d3.sankeyLinkHorizontal())
            .attr("stroke", d => color(d.source.name))
            .attr("stroke-width", d => Math.max(1, d.width))
            .append("title")
            .text(d => `${d.source.name} → ${d.target.name}\n${d.value} lượt chuyển tiếp`);

        // Nodes
        const node = svg.append("g")
            .selectAll("g")
            .data(graph.nodes)
            .join("g");

        node.append("rect")
            .attr("x", d => d.x0)
            .attr("y", d => d.y0)
            .attr("height", d => d.y1 - d.y0)
            .attr("width", d => d.x1 - d.x0)
            .attr("fill", d => color(d.name))
            .attr("stroke", "#fff")
            .attr("stroke-width", 1);

        // Add Names (Labels)
        node.append("text")
            .attr("x", d => d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6)
            .attr("y", d => (d.y1 + d.y0) / 2)
            .attr("dy", "0.35em")
            .attr("text-anchor", d => d.x0 < width / 2 ? "start" : "end")
            .attr("font-size", height > 400 ? "11px" : "9px")
            .attr("font-weight", "bold")
            .attr("fill", "#475569")
            .text(d => d.name.length > 30 ? d.name.substring(0, 27) + '...' : d.name);
    }

    function showModal(title, contentHtml) {
        document.getElementById('modal-title').innerText = title;
        document.getElementById('modal-body').innerHTML = contentHtml;
        document.getElementById('detail-modal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    function closeModal() {
        document.getElementById('detail-modal').classList.add('hidden');
        document.body.style.overflow = '';
    }

    async function viewCoverageDetail() {
        showModal('Bản đồ Tiếp cận học phần chi tiết', `
            <div class="space-y-6">
                <div class="card bg-slate-50/50 border-none shadow-none p-6">
                    <div id="modal-coverage-chart" class="min-h-[500px]"></div>
                </div>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="p-4 bg-indigo-50 rounded-2xl border border-indigo-100">
                        <div class="text-[10px] font-black text-indigo-400 uppercase mb-1">Độ bao phủ trung bình</div>
                        <div id="modal-coverage-avg" class="text-2xl font-black text-indigo-600">--%</div>
                    </div>
                </div>
            </div>
        `);
        
        try {
            const courseId = document.getElementById('course-selector').value;
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&viewall=1`);
            const data = await resp.json();
            
            const interacted = data.dropoff_data.map(d => parseInt(d.interacted_count));
            const avg = Math.round(interacted.reduce((a,b) => a+b, 0) / (interacted.length * (data.global_stats.total_students || 1)) * 100);
            document.getElementById('modal-coverage-avg').innerText = avg + '%';

            new ApexCharts(document.querySelector("#modal-coverage-chart"), {
                series: [{ name: 'Số học sinh đã chạm đến', data: interacted }],
                chart: { type: 'bar', height: 500, toolbar: { show: true } },
                plotOptions: { bar: { borderRadius: 8, columnWidth: '60%', distributed: true } },
                colors: ['#6366f1', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444'],
                xaxis: { 
                    categories: data.dropoff_data.map(d => d.stage.substring(0, 20) + '...'),
                    labels: { rotate: -45, style: { fontSize: '10px', fontWeight: 600 } }
                },
                legend: { show: false }
            }).render();
        } catch (err) { console.error(err); }
    }

    async function viewTreemapDetail() {
        showModal('Bản đồ Sức khỏe Module (Phân tích chi tiết)', `
            <div class="flex flex-wrap gap-3 mb-4 px-1">
                <div class="flex items-center gap-2 text-xs font-black uppercase text-slate-600"><span class="w-3 h-3 rounded-sm bg-red-500"></span> Stuck — cần hỗ trợ</div>
                <div class="flex items-center gap-2 text-xs font-black uppercase text-slate-600"><span class="w-3 h-3 rounded-sm bg-amber-400"></span> Skimming — học lướt</div>
                <div class="flex items-center gap-2 text-xs font-black uppercase text-slate-600"><span class="w-3 h-3 rounded-sm bg-emerald-500"></span> Deep Dive — học sâu</div>
            </div>
            <div id="modal-treemap-full" class="min-h-[600px]"></div>
        `);

        try {
            const courseId = document.getElementById('course-selector').value;
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&viewall=1`);
            const data = await resp.json();

            const grouped = {};
            (data.treemap_data || []).forEach(d => {
                if (!grouped[d.section_name]) grouped[d.section_name] = [];
                let color = '#10b981';
                if (parseFloat(d.stuck_rate) > 30)         color = '#ef4444';
                else if (parseFloat(d.skimming_rate) > 50) color = '#f59e0b';
                grouped[d.section_name].push({
                    x: d.resource_name,
                    y: parseInt(d.total_interactions),
                    fillColor: color,
                    stuck: Math.round(d.stuck_rate),
                    skim: Math.round(d.skimming_rate)
                });
            });

            const series = Object.keys(grouped).map(section => ({ name: section, data: grouped[section] }));

            const chart = new ApexCharts(document.querySelector("#modal-treemap-full"), {
                series: series,
                chart: {
                    height: 600,
                    type: 'treemap',
                    toolbar: { show: false },
                    animations: { enabled: false },
                    events: {
                        rendered: function() {
                            // ApexCharts set stroke qua SVG attribute, không phải CSS
                            // Dùng MutationObserver để catch và override ngay khi attribute được set
                            const el = document.querySelector("#modal-treemap-full");
                            if (!el) return;

                            const applyBorders = () => {
                                // Override stroke attribute trực tiếp trên từng rect
                                el.querySelectorAll('.apexcharts-treemap-rect').forEach(rect => {
                                    rect.setAttribute('stroke', 'rgba(255,255,255,0.75)');
                                    rect.setAttribute('stroke-width', '1');
                                });

                                // Vẽ viền đen 4px bao quanh từng section
                                el.querySelectorAll('.section-border-rect').forEach(r => r.remove());
                                const svgNS = 'http://www.w3.org/2000/svg';
                                el.querySelectorAll('.apexcharts-series').forEach(group => {
                                    const bbox = group.getBBox();
                                    if (bbox.width < 2 || bbox.height < 2) return;
                                    const border = document.createElementNS(svgNS, 'rect');
                                    border.setAttribute('x', bbox.x);
                                    border.setAttribute('y', bbox.y);
                                    border.setAttribute('width', bbox.width);
                                    border.setAttribute('height', bbox.height);
                                    border.setAttribute('fill', 'none');
                                    border.setAttribute('stroke', '#000000');
                                    border.setAttribute('stroke-width', '4');
                                    border.setAttribute('pointer-events', 'none');
                                    border.setAttribute('class', 'section-border-rect');
                                    group.appendChild(border);
                                });
                            };

                            // Chạy ngay + chạy lại sau 100ms để chắc chắn ApexCharts đã xong
                            applyBorders();
                            setTimeout(applyBorders, 100);
                            setTimeout(applyBorders, 300);

                            // MutationObserver: nếu ApexCharts re-set attribute thì override lại
                            const observer = new MutationObserver(() => {
                                observer.disconnect(); // tạm dừng để tránh loop
                                applyBorders();
                                setTimeout(() => observer.observe(el, { subtree: true, attributes: true, attributeFilter: ['stroke', 'stroke-width'] }), 50);
                            });
                            observer.observe(el, { subtree: true, attributes: true, attributeFilter: ['stroke', 'stroke-width'] });
                        }
                    }
                },
                plotOptions: { treemap: { distributed: true, enableShades: false } },
                // stroke tắt — viền sẽ được inject thủ công sau render
                stroke: { show: false },
                dataLabels: {
                    enabled: true,
                    style: { fontSize: '11px', fontWeight: 700, colors: ['#fff'] },
                    formatter: (text, op) => [text, op.value + ' lượt']
                },
                tooltip: {
                    y: {
                        formatter: (val, { seriesIndex, dataPointIndex, w }) => {
                            const item = w.config.series[seriesIndex].data[dataPointIndex];
                            return `${val} lượt | Stuck: ${item.stuck}% | Skimming: ${item.skim}%`;
                        }
                    }
                }
            });
            chart.render();

        } catch (err) {
            console.error(err);
            const el = document.querySelector("#modal-treemap-full");
            if (el) el.innerHTML = `<div class="text-center py-12 text-red-500 font-bold">${err.message}</div>`;
        }
    }

    async function viewMatrixDetail() {
        showModal('Phân tích Mạng lưới Luồng học tập (Sankey Full)', `
            <div class="space-y-6">
                <div class="card bg-white border border-slate-100 p-8">
                    <div id="modal-sankey-full" class="min-h-[700px] w-full"></div>
                </div>
                <p class="text-center text-[10px] text-slate-400 font-bold uppercase tracking-widest">Di chuyển giữa các module nhỏ trong toàn bộ khóa học</p>
            </div>
        `);
        
        try {
            const courseId = document.getElementById('course-selector').value;
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&viewall=1`);
            const data = await resp.json();
            renderSankey(data.transitions, "#modal-sankey-full", 700);
        } catch (err) { console.error(err); }
    }

    async function viewStudentDetail() {
        showModal('Danh sách Hiệu suất Sinh viên', '<div class="py-20 flex justify-center"><div class="w-12 h-12 skeleton rounded-full"></div></div>');
        
        try {
            const courseId = document.getElementById('course-selector').value;
            const week = document.getElementById('week-selector')?.value || 'latest';
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&week=${week}&viewall=1`);
            const data = await resp.json();
            
            if (data.error) throw new Error(data.error);

            let html = `
                <div class="overflow-x-auto">
                    <table class="w-full text-left text-sm">
                        <thead class="bg-slate-50 border-b border-slate-100 uppercase text-[10px] font-black text-slate-400">
                            <tr>
                                <th class="px-6 py-4">Sinh viên</th>
                                <th class="px-6 py-4 text-center">Rủi ro %</th>
                                <th class="px-6 py-4 text-center">Điểm T.Tác</th>
                                <th class="px-6 py-4 text-center">Tiến độ</th>
                                <th class="px-6 py-4 text-right">Hoạt động cuối</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-100">
                            ${data.students && data.students.length > 0 ? data.students.map(s => `
                                <tr class="hover:bg-indigo-50/60 transition-colors cursor-pointer" onclick="openStudentDrilldown('${s.student_key}')" title="Xem chi tiết sinh viên">
                                    <td class="px-6 py-4 font-bold text-slate-700">${s.actor_name || s.student_key}</td>
                                    <td class="px-6 py-4 text-center font-black ${s.dropout_probability_pct > 50 ? 'text-rose-500' : 'text-slate-600'}">${Math.round(s.dropout_probability_pct)}%</td>
                                    <td class="px-6 py-4 text-center font-mono text-xs font-bold">${s.engagement_score}</td>
                                    <td class="px-6 py-4">
                                        <div class="flex items-center gap-3 justify-center">
                                            <div class="w-20 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                                                <div class="h-full bg-indigo-500" style="width:${s.current_progress_pct}%"></div>
                                            </div>
                                            <span class="text-[10px] font-black text-slate-400">${s.current_progress_pct}%</span>
                                        </div>
                                    </td>
                                    <td class="px-6 py-4 text-right text-[10px] font-black text-slate-400 uppercase">${s.last_activity_date}</td>
                                </tr>
                            `).join('') : '<tr><td colspan="5" class="py-10 text-center text-slate-400 italic">Không có dữ liệu sinh viên</td></tr>'}
                        </tbody>
                    </table>
                </div>
            `;
            showModal('Danh sách Hiệu suất Sinh viên', html);
        } catch (err) {
            showModal('Lỗi', `<div class="p-10 text-center text-red-500">${err.message}</div>`);
        }
    }

    async function viewActivityDetail() {
        showModal('Lịch sử Hoạt động Chi tiết', '<div class="py-20 flex justify-center"><div class="w-12 h-12 skeleton rounded-full"></div></div>');
        
        try {
            const courseId = document.getElementById('course-selector').value;
            const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&viewall=1`);
            const data = await resp.json();
            
            if (data.error) throw new Error(data.error);

            let html = `
                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    ${data.my_daily && data.my_daily.length > 0 ? [...data.my_daily].reverse().map(d => `
                        <div class="flex items-center justify-between p-5 bg-slate-50 rounded-[1.5rem] border border-slate-100 hover:border-indigo-200 hover:bg-white hover:shadow-lg hover:shadow-indigo-50 transition-all duration-300 group">
                            <div>
                                <div class="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">${d.day_of_week}</div>
                                <div class="text-sm font-bold text-slate-700">${d.date}</div>
                                <div class="mt-2 flex items-center gap-2">
                                    <span class="px-2 py-0.5 bg-indigo-50 text-indigo-600 text-[10px] font-black rounded-md group-hover:bg-indigo-600 group-hover:text-white transition-colors">SCORE: ${Math.round(d.score)}</span>
                                </div>
                            </div>
                        </div>
                    `).join('') : '<div class="col-span-full py-10 text-center text-slate-400 italic">Không có dữ liệu nhật ký</div>'}
                </div>
            `;
            showModal('Lịch sử Hoạt động Chi tiết', html);
        } catch (err) {
            showModal('Lỗi', `<div class="p-10 text-center text-red-500">${err.message}</div>`);
        }
    }

    document.addEventListener('DOMContentLoaded', fetchData);
    document.getElementById('course-selector').addEventListener('change', fetchData);
    if (isTeacher) document.getElementById('week-selector').addEventListener('change', fetchData);
</script>

<?php echo $OUTPUT->footer(); ?>
