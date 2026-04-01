<?php
/**
 * Student Drilldown Page - Detailed Analytics for Individual Students
 * 
 * Displays comprehensive learning analytics for a single student including
 * engagement trends, risk assessment, time affinity, and actionable insights.
 *
 * @package     local_microlearning
 * @copyright   2024
 * @license     http://www.gnu.org/copyleft/gpl.html GNU GPL v3 or later
 */

require_once(__DIR__ . '/../../config.php');
require_once(__DIR__ . '/lib.php');

// ============================================================================
// 1. PARAMETER VALIDATION
// ============================================================================

// Required parameters
$studentkey = required_param('student_key', PARAM_ALPHANUMEXT);
$coursekey = required_param('course_key', PARAM_RAW);

// Validate parameters are not empty
if (empty($studentkey) || empty($coursekey)) {
    throw new moodle_exception('invalidparameters', 'error', '', null, 
        'student_key and course_key are required parameters');
}

// ============================================================================
// 2. AUTHENTICATION & CONTEXT SETUP
// ============================================================================

// Set up Moodle context based on course
$context = null;
$course = null;

if (is_numeric($coursekey) && $coursekey > 1) {
    try {
        $course = $DB->get_record('course', array('id' => (int)$coursekey), '*', MUST_EXIST);
        $context = context_course::instance($course->id);
        require_login($course);
    } catch (Exception $e) {
        // If course not found, fall back to system context
        $context = context_system::instance();
        require_login();
    }
} else {
    $context = context_system::instance();
    require_login();
}

// ============================================================================
// 3. AUTHORIZATION CHECK
// ============================================================================

// Verify teacher has capability to manage activities in this course
$isteacher = has_capability('moodle/course:manageactivities', $context) || is_siteadmin();

if (!$isteacher) {
    // Log unauthorized access attempt
    $logdata = array(
        'context' => $context,
        'other' => array(
            'student_key' => $studentkey,
            'course_key' => $coursekey,
            'teacher_id' => $USER->id,
            'access_denied' => true
        )
    );
    
    // Display access denied message
    echo $OUTPUT->header();
    echo $OUTPUT->notification('Access Denied: You do not have permission to view student analytics in this course.', 'error');
    echo html_writer::link(new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $coursekey]), 
        'Return to Dashboard', array('class' => 'btn btn-primary'));
    echo $OUTPUT->footer();
    exit;
}

// ============================================================================
// 4. AJAX DATA HANDLER
// ============================================================================

$action = optional_param('action', '', PARAM_ALPHA);
if ($action === 'getdata') {
    header('Content-Type: application/json');
    
    try {
        // Establish database connection
        $conn = local_microlearning_get_sqlserver_connection();
        if (!$conn) {
            throw new Exception('PostgreSQL connection failed');
        }
        
        // Verify teacher authorization
        if (!$isteacher) {
            throw new Exception('Access denied');
        }
        
        // Initialize response data array
        $data = [];
        
        // Verify student exists
        $stmt = $conn->prepare("
            SELECT actor_id, actor_name 
            FROM datamart.dim_actor 
            WHERE actor_id = ?
            LIMIT 1
        ");
        $stmt->execute([$studentkey]);
        $student = $stmt->fetch(PDO::FETCH_ASSOC);
        
        if (!$student) {
            throw new Exception('Student not found');
        }
        
        $data['student_name'] = $student['actor_name'];
        
        // Get course name
        $stmt = $conn->prepare("
            SELECT course_name 
            FROM datamart.dim_course 
            WHERE CAST(course_key AS VARCHAR) = ?
            LIMIT 1
        ");
        $stmt->execute([$coursekey]);
        $coursedata = $stmt->fetch(PDO::FETCH_ASSOC);
        $data['course_name'] = $coursedata ? $coursedata['course_name'] : 'Unknown Course';
        
        // 1. Overview Metrics - Current engagement and risk
        $stmt = $conn->prepare("
            SELECT engagement_score, risk_level, dropout_probability_pct, risk_score
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
            ORDER BY year DESC, week_of_year DESC
            LIMIT 1
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $riskData = $stmt->fetch(PDO::FETCH_ASSOC);
        
        // 2. Lifecycle data - Progress and activity
        $stmt = $conn->prepare("
            SELECT current_progress_pct, days_since_last_activity, 
                   current_status, completed_module_count, last_activity_date
            FROM datamart.fact_student_course_lifecycle
            WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
            LIMIT 1
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $lifecycleData = $stmt->fetch(PDO::FETCH_ASSOC);
        
        // Combine overview metrics
        $data['overview'] = [
            'engagement_score' => $riskData ? (int)$riskData['engagement_score'] : 0,
            'risk_level' => $riskData ? $riskData['risk_level'] : 'Unknown',
            'dropout_probability_pct' => $riskData ? (float)$riskData['dropout_probability_pct'] : 0,
            'risk_score' => $riskData ? (int)$riskData['risk_score'] : 0,
            'current_progress_pct' => $lifecycleData ? (int)$lifecycleData['current_progress_pct'] : 0,
            'days_since_last_activity' => $lifecycleData ? (int)$lifecycleData['days_since_last_activity'] : 0,
            'current_status' => $lifecycleData ? $lifecycleData['current_status'] : 'No Data',
            'completed_module_count' => $lifecycleData ? (int)$lifecycleData['completed_module_count'] : 0,
            'last_activity_date' => $lifecycleData ? $lifecycleData['last_activity_date'] : 'N/A'
        ];
        
        // 3. Engagement Trend - 12 weeks of data
        $stmt = $conn->prepare("
            SELECT week_of_year, year, engagement_score, risk_level
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
            ORDER BY year DESC, week_of_year DESC
            LIMIT 12
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $data['engagement_trend'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);
        
        // 4. Class average for comparison
        $stmt = $conn->prepare("
            SELECT week_of_year, year, avg_engagement_score
            FROM datamart.fact_class_engagement_distribution
            WHERE CAST(course_key AS VARCHAR) = ?
            ORDER BY year DESC, week_of_year DESC
            LIMIT 12
        ");
        $stmt->execute([$coursekey]);
        $data['class_average'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);
        
        // 5. Time Affinity
        $stmt = $conn->prepare("
            SELECT time_slot, efficiency_index, total_engagement_score, session_count
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
        $stmt->execute([$studentkey, $coursekey]);
        $data['time_affinity'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
        
        // 6. Engagement Depth - all resources, not started if no interaction
        $stmt = $conn->prepare("
            SELECT 
                r.resource_name,
                COALESCE(d.engagement_type, 'Not Started') as engagement_type,
                COALESCE(d.depth_ratio, 0) as depth_ratio,
                r.resource_key
            FROM datamart.dim_resource r
            LEFT JOIN datamart.fact_student_engagement_depth d 
                ON CAST(d.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
                AND d.student_key = ?
                AND CAST(d.course_key AS VARCHAR) = ?
            WHERE CAST(r.course_key AS VARCHAR) = ?
            ORDER BY 
                CASE COALESCE(d.engagement_type, 'Not Started')
                    WHEN 'Stuck' THEN 1
                    WHEN 'Skimming' THEN 2
                    WHEN 'Deep Dive' THEN 3
                    WHEN 'Normal' THEN 4
                    ELSE 5
                END,
                COALESCE(d.depth_ratio, 0) DESC
        ");
        $stmt->execute([$studentkey, $coursekey, $coursekey]);
        $data['engagement_depth'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
        
        // 7. Deadline Proximity - Top 5 upcoming deadlines
        $stmt = $conn->prepare("
            SELECT 
                r.resource_name,
                p.deadline_date,
                p.pressure_level,
                EXTRACT(EPOCH FROM (p.deadline_date - NOW())) / 3600 AS hours_before_deadline
            FROM datamart.fact_student_deadline_proximity p
            JOIN datamart.dim_resource r ON CAST(p.resource_key AS VARCHAR) = CAST(r.resource_key AS VARCHAR)
            WHERE p.student_key = ? AND CAST(p.course_key AS VARCHAR) = ?
                AND p.deadline_date > NOW()
            ORDER BY p.deadline_date ASC
            LIMIT 5
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $data['deadlines'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
        
        // 8. Daily Activity - 90 days
        $stmt = $conn->prepare("
            SELECT 
                t.year,
                t.month,
                t.date,
                t.day_of_week,
                f.engagement_score,
                f.total_resource_access,
                f.total_quiz_attempt
            FROM datamart.fact_daily_student_engagement f
            JOIN datamart.dim_time t ON f.date_key = t.time_id
            WHERE f.student_key = ? AND CAST(f.course_key AS VARCHAR) = ?
            ORDER BY t.year DESC, t.month DESC, t.date DESC
            LIMIT 90
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $data['daily_activity'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC) ?: []);
        
        // 9. Activity Transitions
        $stmt = $conn->prepare("
            SELECT 
                r1.resource_name AS from_resource,
                r2.resource_name AS to_resource,
                t.transition_count,
                CAST(t.from_resource_key AS VARCHAR) AS from_key,
                CAST(t.to_resource_key AS VARCHAR) AS to_key
            FROM datamart.fact_activity_transitions t
            JOIN datamart.dim_resource r1 ON CAST(t.from_resource_key AS VARCHAR) = CAST(r1.resource_key AS VARCHAR)
            JOIN datamart.dim_resource r2 ON CAST(t.to_resource_key AS VARCHAR) = CAST(r2.resource_key AS VARCHAR)
            WHERE CAST(t.course_key AS VARCHAR) = ?
                AND EXISTS (
                    SELECT 1 FROM datamart.fact_daily_student_engagement e
                    WHERE e.student_key = ? AND CAST(e.course_key AS VARCHAR) = ?
                )
            ORDER BY t.transition_count DESC
            LIMIT 20
        ");
        $stmt->execute([$coursekey, $studentkey, $coursekey]);
        $data['transitions'] = $stmt->fetchAll(PDO::FETCH_ASSOC) ?: [];
        
        // 10. Lifecycle Milestones
        $stmt = $conn->prepare("
            SELECT 
                milestone_25_date,
                milestone_50_date,
                milestone_75_date,
                completion_date,
                current_progress_pct,
                completed_module_count,
                current_status,
                dropout_date
            FROM datamart.fact_student_course_lifecycle
            WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $data['lifecycle_milestones'] = $stmt->fetch(PDO::FETCH_ASSOC) ?: [];
        
        // 11. Class comparison & percentile (Requirement 10)
        $stmt = $conn->prepare("
            WITH ranked AS (
                SELECT student_key,
                    PERCENT_RANK() OVER (ORDER BY AVG(engagement_score)) AS pr
                FROM datamart.fact_risk_student_weekly
                WHERE CAST(course_key AS VARCHAR) = ?
                GROUP BY student_key
            )
            SELECT COALESCE(ROUND(pr * 100)::int, 0) AS percentile_rank
            FROM ranked
            WHERE student_key = ?
        ");
        $stmt->execute([$coursekey, $studentkey]);
        $pctRow = $stmt->fetch(PDO::FETCH_ASSOC);
        $percentileRank = $pctRow ? (int)$pctRow['percentile_rank'] : 0;

        $stmt = $conn->prepare("
            WITH latest AS (
                SELECT DISTINCT ON (student_key) student_key, engagement_score, risk_score
                FROM datamart.fact_risk_student_weekly
                WHERE CAST(course_key AS VARCHAR) = ?
                ORDER BY student_key, year DESC, week_of_year DESC
            )
            SELECT COALESCE(AVG(engagement_score), 0)::float AS class_avg_engagement,
                   COALESCE(AVG(risk_score), 0)::float AS class_avg_risk
            FROM latest
        ");
        $stmt->execute([$coursekey]);
        $classLatest = $stmt->fetch(PDO::FETCH_ASSOC) ?: ['class_avg_engagement' => 0, 'class_avg_risk' => 0];

        $stmt = $conn->prepare("
            SELECT COALESCE(AVG(engagement_score), 0)::float AS student_avg_engagement,
                   COALESCE(AVG(risk_score), 0)::float AS student_avg_risk
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = ? AND CAST(course_key AS VARCHAR) = ?
        ");
        $stmt->execute([$studentkey, $coursekey]);
        $stuAgg = $stmt->fetch(PDO::FETCH_ASSOC) ?: ['student_avg_engagement' => 0, 'student_avg_risk' => 0];

        $stmt = $conn->prepare("
            SELECT COALESCE(AVG(current_progress_pct), 0)::float AS class_avg_progress
            FROM datamart.fact_student_course_lifecycle
            WHERE CAST(course_key AS VARCHAR) = ?
        ");
        $stmt->execute([$coursekey]);
        $classProg = $stmt->fetch(PDO::FETCH_ASSOC);
        $classAvgProgress = $classProg ? (float)$classProg['class_avg_progress'] : 0;

        $stuProgress = isset($data['overview']['current_progress_pct']) ? (float)$data['overview']['current_progress_pct'] : 0;

        $ce = (float)$stuAgg['student_avg_engagement'];
        $cc = (float)$classLatest['class_avg_engagement'];
        $engDiffPct = ($cc > 0) ? (($ce - $cc) / $cc) * 100 : 0;

        $cr = (float)$stuAgg['student_avg_risk'];
        $crClass = (float)$classLatest['class_avg_risk'];
        $riskDiffPct = ($crClass > 0) ? (($cr - $crClass) / $crClass) * 100 : 0;

        $progDiffPct = ($classAvgProgress > 0) ? (($stuProgress - $classAvgProgress) / $classAvgProgress) * 100 : 0;

        $data['comparison'] = [
            'student_avg_engagement' => round($ce, 1),
            'class_avg_engagement' => round($cc, 1),
            'engagement_diff_pct' => round($engDiffPct, 1),
            'student_avg_risk' => round($cr, 1),
            'class_avg_risk' => round($crClass, 1),
            'risk_diff_pct' => round($riskDiffPct, 1),
            'student_progress_pct' => round($stuProgress, 1),
            'class_avg_progress' => round($classAvgProgress, 1),
            'progress_diff_pct' => round($progDiffPct, 1),
            'percentile_rank' => $percentileRank,
            'below_avg_engagement' => ($engDiffPct < -30),
        ];

        $crit = 0;
        foreach ($data['deadlines'] as $d) {
            if (isset($d['pressure_level']) && strcasecmp((string)$d['pressure_level'], 'Critical') === 0) {
                $crit++;
            }
        }
        $data['critical_deadline_count'] = $crit;
        $data['server_time_iso'] = gmdate('c');

        // Return JSON response
        echo json_encode($data);
        
    } catch (Exception $e) {
        // Return error response
        http_response_code(500);
        echo json_encode([
            'error' => $e->getMessage(),
            'success' => false
        ]);
    }
    
    exit;
}

// ============================================================================
// 5. PAGE CONFIGURATION
// ============================================================================

$PAGE->set_url(new moodle_url('/local/microlearning/student_detail.php', [
    'student_key' => $studentkey,
    'course_key' => $coursekey
]));
$PAGE->set_context($context);
$PAGE->set_title('Student Analytics');
$PAGE->set_heading('Student Drilldown');

// ============================================================================
// 6. VERIFY STUDENT EXISTS IN DATAMART
// ============================================================================

try {
    $conn = local_microlearning_get_sqlserver_connection();
    if (!$conn) {
        throw new Exception('Database connection failed');
    }
    
    // Check if student exists in dim_actor
    $stmt = $conn->prepare("
        SELECT actor_id, actor_name 
        FROM datamart.dim_actor 
        WHERE actor_id = ?
        LIMIT 1
    ");
    $stmt->execute([$studentkey]);
    $student = $stmt->fetch(PDO::FETCH_ASSOC);
    
    if (!$student) {
        // Student not found - display error
        echo $OUTPUT->header();
        echo $OUTPUT->notification('Student not found. The student data may not have been processed yet or the student_key is invalid.', 'error');
        echo html_writer::link(new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $coursekey]), 
            'Return to Dashboard', array('class' => 'btn btn-primary'));
        echo $OUTPUT->footer();
        exit;
    }
    
    // Get course name
    $stmt = $conn->prepare("
        SELECT course_name 
        FROM datamart.dim_course 
        WHERE CAST(course_key AS VARCHAR) = ?
        LIMIT 1
    ");
    $stmt->execute([$coursekey]);
    $coursedata = $stmt->fetch(PDO::FETCH_ASSOC);
    $coursename = $coursedata ? $coursedata['course_name'] : 'Unknown Course';
    
} catch (Exception $e) {
    // Database error
    error_log('Student Drilldown - Database error: ' . $e->getMessage());
    echo $OUTPUT->header();
    echo $OUTPUT->notification('Unable to load student analytics data. Please try again later.', 'error');
    echo html_writer::link(new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $coursekey]), 
        'Return to Dashboard', array('class' => 'btn btn-primary'));
    echo $OUTPUT->footer();
    exit;
}

// ============================================================================
// 7. AUDIT LOGGING
// ============================================================================

// Log successful page access
$logdata = array(
    'context' => $context,
    'other' => array(
        'student_key' => $studentkey,
        'course_key' => $coursekey,
        'teacher_id' => $USER->id,
        'student_name' => $student['actor_name'],
        'course_name' => $coursename,
        'timestamp' => time(),
        'access_granted' => true
    )
);

// Create audit log entry (using Moodle's event system if available)
// For now, we'll use error_log for audit trail
error_log(sprintf(
    'AUDIT: Student Drilldown Access - Teacher: %d, Student: %s, Course: %s, Time: %s',
    $USER->id,
    $studentkey,
    $coursekey,
    date('Y-m-d H:i:s')
));

// ============================================================================
// 8. RENDER PAGE
// ============================================================================

echo $OUTPUT->header();
?>

<!-- Style & Assets -->
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>
<script src="https://d3js.org/d3.v7.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/d3-sankey@0.12.3/dist/d3-sankey.min.js"></script>

<!-- External CSS -->
<link rel="stylesheet" href="<?php echo new moodle_url('/local/microlearning/assets/css/student_detail.css'); ?>">

<!-- Sticky Breadcrumb Navigation -->
<div class="breadcrumb-nav">
    <div class="max-w-[1600px] mx-auto px-6 py-4">
        <div class="flex items-center gap-4">
            <!-- Back Button -->
            <a href="<?php echo new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $coursekey]); ?>" 
               class="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-100 hover:bg-slate-200 transition-colors group">
                <svg class="w-5 h-5 text-slate-600 group-hover:text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7"/>
                </svg>
            </a>
            
            <!-- Breadcrumb Trail -->
            <nav aria-label="breadcrumb" class="flex items-center gap-2 text-sm">
                <a href="<?php echo new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $coursekey]); ?>" 
                   class="text-slate-600 hover:text-indigo-600 font-medium transition-colors">
                    Dashboard
                </a>
                <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
                <span class="text-slate-600 font-medium">
                    <?php echo s($coursename); ?>
                </span>
                <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
                <span class="text-slate-900 font-bold" aria-current="page">
                    <?php echo s($student['actor_name']); ?>
                </span>
            </nav>
        </div>
    </div>
</div>

<!-- Student Drilldown Page Content -->
<div class="max-w-[1600px] mx-auto p-6 space-y-8">
    <!-- Page Header -->
    <div class="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
        <div class="flex flex-col gap-2">
            <h1 class="text-3xl font-extrabold text-slate-900">
                Student Analytics: <span class="text-indigo-600"><?php echo s($student['actor_name']); ?></span>
            </h1>
            <p class="text-slate-500">Detailed learning analytics and performance insights</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
            <span id="last-updated" class="text-xs font-medium text-slate-500 px-3 py-1.5 bg-white border border-slate-200 rounded-lg">—</span>
            <button type="button" id="btn-refresh-data"
                class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 shadow-sm">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                Refresh Data
            </button>
            <button type="button" id="btn-export-print"
                class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-white border border-slate-200 text-slate-700 text-sm font-semibold hover:bg-slate-50">
                Export report
            </button>
        </div>
    </div>
    <p id="refresh-toast" class="hidden text-sm text-emerald-600 font-medium mt-2"></p>

    <div id="drilldown-print-area">
    
    <!-- Loading State -->
    <div id="loading-state" class="card">
        <div class="flex items-center justify-center gap-3 py-8">
            <svg class="animate-spin h-8 w-8 text-indigo-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span class="text-lg font-medium text-slate-700">Loading student analytics...</span>
        </div>
    </div>

    <!-- Overview Metrics Section -->
    <div id="overview-metrics" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Overview Metrics<span title="Tổng quan hiệu suất học tập của học sinh tuần gần nhất" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <!-- Engagement Score Card -->
            <div class="card">
                <div class="flex items-start justify-between">
                    <div>
                        <p class="text-sm font-medium text-slate-500 mb-1">Engagement Score<span title="Mức độ tham gia học tập (0-100 điểm). Càng cao càng tốt" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></p>
                        <p id="engagement-score" class="text-3xl font-bold text-slate-900">--</p>
                        <p class="text-xs text-slate-500 mt-1">out of 100</p>
                    </div>
                    <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center">
                        <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                        </svg>
                    </div>
                </div>
            </div>

            <!-- Risk Level Card -->
            <div class="card">
                <div class="flex items-start justify-between">
                    <div>
                        <p class="text-sm font-medium text-slate-500 mb-1">Risk Level<span title="Nguy cơ bỏ học: Low (thấp) / Medium (trung bình) / High (cao) / Critical (rất cao)" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></p>
                        <div class="flex items-center gap-2">
                            <p id="risk-level" class="text-3xl font-bold text-slate-900">--</p>
                            <span id="risk-indicator" class="hidden w-3 h-3 rounded-full"></span>
                        </div>
                        <p id="dropout-probability" class="text-xs text-slate-500 mt-1">--% dropout probability</p>
                    </div>
                    <div id="risk-icon" class="flex-shrink-0 w-12 h-12 rounded-xl bg-slate-50 flex items-center justify-center">
                        <svg class="w-6 h-6 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                        </svg>
                    </div>
                </div>
            </div>

            <!-- Progress Card -->
            <div class="card">
                <div class="flex items-start justify-between">
                    <div class="w-full">
                        <p class="text-sm font-medium text-slate-500 mb-1">Course Progress<span title="Phần trăm (%) bài học đã hoàn thành" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></p>
                        <p id="progress-pct" class="text-3xl font-bold text-slate-900">--%</p>
                        <div class="mt-3 w-full bg-slate-200 rounded-full h-2">
                            <div id="progress-bar" class="bg-indigo-600 h-2 rounded-full transition-all duration-500" style="width: 0%"></div>
                        </div>
                        <p id="completed-modules" class="text-xs text-slate-500 mt-2">-- modules completed</p>
                    </div>
                </div>
            </div>

            <!-- Activity Status Card -->
            <div class="card">
                <div class="flex items-start justify-between">
                    <div>
                        <p class="text-sm font-medium text-slate-500 mb-1">Last Activity<span title="Số ngày kể từ lần học cuối cùng" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></p>
                        <p id="days-since-activity" class="text-3xl font-bold text-slate-900">--</p>
                        <p class="text-xs text-slate-500 mt-1">days ago</p>
                        <div id="activity-warning" class="hidden mt-2 flex items-center gap-1 text-xs text-amber-600">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                            </svg>
                            <span>Inactive >7 days</span>
                        </div>
                    </div>
                    <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center">
                        <svg class="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                </div>
            </div>
        </div>

        <!-- Lifecycle Status Banner -->
        <div id="lifecycle-status-banner" class="card mt-6">
            <div class="flex items-center gap-3">
                <div id="status-icon" class="flex-shrink-0 w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center">
                    <svg class="w-5 h-5 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                    </svg>
                </div>
                <div>
                    <p class="text-sm font-medium text-slate-500">Current Status</p>
                    <p id="current-status" class="text-lg font-bold text-slate-900">--</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Engagement Trend Chart Section -->
    <div id="engagement-trend-section" class="hidden">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-slate-900">Engagement Trend<span title="Xu hướng tham gia học tập theo tuần so với trung bình lớp" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
            <button onclick="viewTrendDetailSD()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
        </div>
        <div class="card">
            <div id="engagement-trend-chart"></div>
        </div>
    </div>

    <!-- Time Affinity Chart Section -->
    <div id="time-affinity-section" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Time Affinity Analysis<span title="Khung giờ nào học sinh học hiệu quả nhất trong ngày" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        <div class="card">
            <div id="time-affinity-chart"></div>
            <div id="time-recommendation" class="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                <div class="flex items-start gap-3">
                    <div class="flex-shrink-0 w-10 h-10 rounded-lg bg-indigo-100 flex items-center justify-center">
                        <svg class="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                        </svg>
                    </div>
                    <div>
                        <p class="text-sm font-medium text-indigo-900 mb-1">Recommendation</p>
                        <p id="time-recommendation-text" class="text-sm text-indigo-700">--</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Class comparison -->
    <div id="comparison-section" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Class comparison<span title="So sánh học sinh với trung bình lớp" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        <div class="card">
            <div id="below-avg-banner" class="hidden mb-4 p-3 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm font-medium">
                Engagement is more than 30% below the class average — consider additional support.
            </div>
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
                <div class="p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <p class="text-slate-500 font-medium mb-1">Avg engagement vs class</p>
                    <p id="cmp-eng" class="text-lg font-bold text-slate-900">—</p>
                </div>
                <div class="p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <p class="text-slate-500 font-medium mb-1">Avg risk vs class</p>
                    <p id="cmp-risk" class="text-lg font-bold text-slate-900">—</p>
                </div>
                <div class="p-4 rounded-xl bg-slate-50 border border-slate-100">
                    <p class="text-slate-500 font-medium mb-1">Progress vs class</p>
                    <p id="cmp-prog" class="text-lg font-bold text-slate-900">—</p>
                </div>
                <div class="p-4 rounded-xl bg-indigo-50 border border-indigo-100">
                    <p class="text-slate-500 font-medium mb-1">Engagement percentile</p>
                    <p id="cmp-pct" class="text-lg font-bold text-indigo-900">—</p>
                </div>
            </div>
        </div>
    </div>

    <!-- Engagement depth -->
    <div id="depth-section" class="hidden">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-slate-900">Engagement depth by resource<span title="Mức độ tương tác với từng tài liệu học tập" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
            <button onclick="viewDepthDetailSD()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
        </div>
        <div class="card overflow-x-auto">
            <div class="flex flex-wrap items-center gap-3 mb-4">
                <label for="depth-filter" class="text-sm font-medium text-slate-600">Filter</label>
                <select id="depth-filter" class="rounded-lg border border-slate-200 text-sm px-3 py-2 bg-white">
                    <option value="">All</option>
                    <option value="Stuck">Stuck</option>
                    <option value="Skimming">Skimming</option>
                    <option value="Deep Dive">Deep Dive</option>
                    <option value="Normal">Normal</option>
                    <option value="Not Started">Not Started</option>
                </select>
            </div>
            <table class="min-w-full text-sm text-left">
                <thead class="text-xs uppercase text-slate-400 border-b border-slate-100">
                    <tr>
                        <th class="py-3 pr-4">Resource</th>
                        <th class="py-3 pr-4">Category</th>
                        <th class="py-3 pr-4">Depth ratio</th>
                    </tr>
                </thead>
                <tbody id="depth-table-body" class="divide-y divide-slate-100"></tbody>
            </table>
            <p id="depth-empty" class="hidden text-slate-400 italic py-6">No engagement depth data.</p>
        </div>
    </div>

    <!-- Deadlines -->
    <div id="deadlines-section" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Upcoming deadlines<span title="Các bài tập sắp đến hạn nộp" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        <div class="card space-y-3" id="deadlines-list"></div>
    </div>

    <!-- Activity transitions (Sankey) -->
    <div id="transitions-section" class="hidden">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-slate-900">Activity transition flow<span title="Luồng chuyển đổi giữa các tài liệu học tập" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
            <button onclick="viewTransitionsDetailSD()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
        </div>
        <div class="card">
            <p id="review-loop-banner" class="hidden mb-3 text-sm font-semibold text-orange-700 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2">Review loop detected</p>
            <p id="back-edge-note" class="hidden mb-3 text-xs text-slate-600">Backward transitions (orange) are listed below the chart.</p>
            <div id="student-sankey" class="w-full min-h-[320px]"></div>
            <ul id="back-edges-list" class="hidden mt-4 space-y-2 text-sm"></ul>
        </div>
    </div>

    <!-- Lifecycle milestones -->
    <div id="lifecycle-section" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Course lifecycle milestones<span title="Các mốc tiến độ quan trọng: 25%, 50%, 75%, 100%" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        <div class="card space-y-4">
            <div id="dropout-banner" class="hidden p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm"></div>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm" id="milestone-grid"></div>
            <p id="est-completion" class="text-sm text-slate-600"></p>
        </div>
    </div>

    <!-- Daily heatmap -->
    <div id="heatmap-section" class="hidden">
        <div class="flex items-center justify-between mb-4">
            <h2 class="text-xl font-bold text-slate-900">Daily activity (90 days)<span title="Lịch sử học tập 90 ngày gần nhất" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
            <button onclick="viewHeatmapDetailSD()" class="text-[10px] font-black text-indigo-600 hover:text-indigo-800 uppercase tracking-widest bg-indigo-50 px-3 py-1.5 rounded-lg transition-all active:scale-95">Xem chi tiết</button>
        </div>
        <div class="card">
            <p class="text-xs text-slate-500 mb-3">Gray = no activity; darker = higher engagement. Red outline = inactive streak &gt; 3 days.</p>
            <div id="daily-heatmap" class="flex flex-wrap gap-1"></div>
        </div>
    </div>

    <!-- Insights -->
    <div id="insights-section" class="hidden">
        <h2 class="text-xl font-bold text-slate-900 mb-4">Insights &amp; recommendations<span title="Gợi ý hỗ trợ học sinh dựa trên dữ liệu" style="cursor:help;color:#94a3b8;"><svg style="display:inline-block;width:16px;height:16px;margin-left:6px;vertical-align:middle;" fill="none" stroke="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 16v-4m0-4h.01"/></svg></span></h2>
        <div class="card space-y-3" id="insights-list"></div>
    </div>

    </div><!-- /#drilldown-print-area -->

    <!-- Error State -->
    <div id="error-state" class="hidden card">
        <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 rounded-xl bg-red-50 flex items-center justify-center">
                <svg class="w-6 h-6 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
            </div>
            <div>
                <h3 class="text-lg font-bold text-slate-900 mb-1">Unable to Load Data</h3>
                <p id="error-message" class="text-slate-600">An error occurred while loading student analytics.</p>
            </div>
        </div>
    </div>
</div>
<!-- Pass PHP variables to JavaScript -->
<script>
    window.STUDENT_KEY = '<?php echo addslashes($studentkey); ?>';
    window.COURSE_KEY = '<?php echo addslashes($coursekey); ?>';
</script>

<!-- External JavaScript (load in order) -->
<script src="<?php echo new moodle_url('/local/microlearning/assets/js/student_detail.js'); ?>?v=<?php echo time(); ?>"></script>
<script src="<?php echo new moodle_url('/local/microlearning/assets/js/student_detail_render.js'); ?>?v=<?php echo time(); ?>"></script>
<script src="<?php echo new moodle_url('/local/microlearning/assets/js/student_detail_main.js'); ?>?v=<?php echo time(); ?>"></script>
<script>
// ── Student Detail — modal helper ──────────────────────────────────────────
const SD_MODAL_ID = 'sd-detail-modal';

function sdShowModal(title, html) {
    let modal = document.getElementById(SD_MODAL_ID);
    if (!modal) {
        modal = document.createElement('div');
        modal.id = SD_MODAL_ID;
        modal.className = 'fixed inset-0 z-[9999] flex items-center justify-center p-2 sm:p-4';
        modal.innerHTML = `
            <div class="absolute inset-0 bg-slate-900/60 backdrop-blur-sm" onclick="sdCloseModal()"></div>
            <div class="bg-white rounded-[2rem] shadow-2xl w-full max-w-[95vw] h-full max-h-[95vh] flex flex-col relative z-10 overflow-hidden border border-slate-100">
                <div class="p-6 border-b border-slate-100 flex justify-between items-center sticky top-0 bg-white z-20">
                    <h2 id="sd-modal-title" class="text-2xl font-extrabold text-slate-800"></h2>
                    <button onclick="sdCloseModal()" class="p-2 hover:bg-slate-100 rounded-full">
                        <svg class="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>
                <div id="sd-modal-body" class="p-4 md:p-8 overflow-y-auto flex-grow"></div>
            </div>`;
        document.body.appendChild(modal);
    }
    document.getElementById('sd-modal-title').textContent = title;
    document.getElementById('sd-modal-body').innerHTML = html;
    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
}

function sdCloseModal() {
    const modal = document.getElementById(SD_MODAL_ID);
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = '';
}

// Engagement Trend — full history
function viewTrendDetailSD() {
    const cached = getCachedData(window.STUDENT_KEY, window.COURSE_KEY);
    if (!cached) return;
    sdShowModal('Xu hướng tương tác — Toàn bộ lịch sử', `<div id="sd-trend-full" class="min-h-[500px]"></div>`);
    setTimeout(() => {
        const trend = cached.engagement_trend || [];
        const classAvg = cached.class_average || [];
        const classMap = {};
        classAvg.forEach(c => { classMap[`${c.year}-${c.week_of_year}`] = parseFloat(c.avg_engagement_score) || 0; });
        new ApexCharts(document.querySelector('#sd-trend-full'), {
            series: [
                { name: 'Học sinh', data: trend.map(t => parseInt(t.engagement_score) || 0) },
                { name: 'TB lớp', data: trend.map(t => classMap[`${t.year}-${t.week_of_year}`] || 0) }
            ],
            chart: { type: 'line', height: 500, toolbar: { show: true } },
            stroke: { width: [3, 2], curve: 'smooth', dashArray: [0, 5] },
            xaxis: { categories: trend.map(t => `T${t.week_of_year}/${t.year}`) },
            colors: ['#6366f1', '#94a3b8'],
            yaxis: { min: 0, max: 100, title: { text: 'Điểm tương tác' } },
            legend: { position: 'top' },
            annotations: { yaxis: [{ y: 50, borderColor: '#ef4444', label: { text: 'Ngưỡng rủi ro', style: { color: '#ef4444' } } }] }
        }).render();
    }, 50);
}

// Engagement Depth — full table with chart
function viewDepthDetailSD() {
    const cached = getCachedData(window.STUDENT_KEY, window.COURSE_KEY);
    if (!cached) return;
    const depth = cached.engagement_depth || [];
    const typeColor = { 'Stuck': 'text-amber-600 font-bold', 'Skimming': 'text-sky-600', 'Deep Dive': 'text-emerald-600 font-bold', 'Normal': 'text-slate-500', 'Not Started': 'text-slate-300' };
    const typeIcon = { 'Stuck': '⚠', 'Skimming': 'ⓘ', 'Deep Dive': '✓', 'Normal': '·', 'Not Started': '○' };
    sdShowModal('Độ sâu tương tác — Tất cả tài nguyên', `
        <div id="sd-depth-bar" class="min-h-[300px] mb-6"></div>
        <table class="w-full text-sm text-left">
            <thead class="text-[10px] uppercase text-slate-400 border-b font-black">
                <tr><th class="py-3 pr-4">Tài nguyên</th><th class="py-3 pr-4">Loại</th><th class="py-3 pr-4">Depth ratio</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                ${depth.map(r => `<tr class="hover:bg-slate-50">
                    <td class="py-2 pr-4 font-medium text-slate-800">${escapeHtml(r.resource_name || '')}</td>
                    <td class="py-2 pr-4 ${typeColor[r.engagement_type] || ''}">${typeIcon[r.engagement_type] || ''} ${r.engagement_type}</td>
                    <td class="py-2 pr-4 font-mono">${r.depth_ratio != null ? Number(r.depth_ratio).toFixed(2) : '—'}</td>
                </tr>`).join('')}
            </tbody>
        </table>
    `);
    setTimeout(() => {
        const chartData = depth.filter(r => r.engagement_type !== 'Not Started');
        if (!chartData.length) return;
        new ApexCharts(document.querySelector('#sd-depth-bar'), {
            series: [{ name: 'Depth ratio', data: chartData.map(r => parseFloat(r.depth_ratio) || 0) }],
            chart: { type: 'bar', height: 300, toolbar: { show: false } },
            plotOptions: { bar: { borderRadius: 6, distributed: true } },
            colors: chartData.map(r => r.engagement_type === 'Stuck' ? '#f59e0b' : r.engagement_type === 'Skimming' ? '#38bdf8' : r.engagement_type === 'Deep Dive' ? '#10b981' : '#94a3b8'),
            xaxis: { categories: chartData.map(r => (r.resource_name || '').substring(0, 18) + '...'), labels: { style: { fontSize: '10px' } } },
            legend: { show: false },
            yaxis: { title: { text: 'Depth ratio' } }
        }).render();
    }, 50);
}

// Activity Transitions — full table
function viewTransitionsDetailSD() {
    const cached = getCachedData(window.STUDENT_KEY, window.COURSE_KEY);
    if (!cached) return;
    const trans = cached.transitions || [];
    sdShowModal('Luồng chuyển tiếp tài nguyên — Đầy đủ', `
        <table class="w-full text-sm text-left">
            <thead class="text-[10px] uppercase text-slate-400 border-b font-black">
                <tr><th class="py-3 pr-4">Từ</th><th class="py-3 pr-4">Đến</th><th class="py-3 pr-4 text-center">Số lần</th></tr>
            </thead>
            <tbody class="divide-y divide-slate-100">
                ${trans.length ? trans.map(t => `<tr class="hover:bg-slate-50">
                    <td class="py-2 pr-4 text-slate-700">${escapeHtml(t.from_resource || '')}</td>
                    <td class="py-2 pr-4 text-slate-700">${escapeHtml(t.to_resource || '')}</td>
                    <td class="py-2 pr-4 text-center font-mono font-bold">${t.transition_count}</td>
                </tr>`).join('') : '<tr><td colspan="3" class="py-8 text-center text-slate-400 italic">Không có dữ liệu</td></tr>'}
            </tbody>
        </table>
    `);
}

// Daily Heatmap — 365 days
function viewHeatmapDetailSD() {
    sdShowModal('Lịch sử hoạt động hàng ngày — 365 ngày', `<div id="sd-heatmap-full" class="flex flex-wrap gap-1 p-2"></div><p class="text-xs text-slate-400 mt-3 px-2">Xám = không hoạt động | Xanh đậm = tương tác cao | Viền đỏ = chuỗi không hoạt động > 3 ngày</p>`);
    const studentKey = window.STUDENT_KEY;
    const courseKey = window.COURSE_KEY;
    fetch(`?action=getdata&student_key=${encodeURIComponent(studentKey)}&course_key=${encodeURIComponent(courseKey)}&viewall=1`)
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('sd-heatmap-full');
            if (!container) return;
            renderHeatmapSection(data.daily_activity || [], container);
        })
        .catch(err => console.error(err));
}
</script>

<?php
echo $OUTPUT->footer();
?>
