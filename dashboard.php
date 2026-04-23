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

require_login();
$context = context_system::instance();
$isteacher = has_capability('moodle/course:manageactivities', $context) || is_siteadmin();
$currentuserid = $USER->id;
$courseid = optional_param('courseid', '1', PARAM_RAW);
$week = optional_param('week', 'latest', PARAM_RAW);

// Page Setup
$PAGE->set_url(new moodle_url('/local/microlearning/dashboard.php', ['courseid' => $courseid, 'week' => $week]));
$PAGE->set_context($context);
$PAGE->set_title('Datamart Analytics');
$PAGE->set_heading('Learning Analytics Dashboard');

// AJAX Data Handler
$action = optional_param('action', '', PARAM_ALPHA);
if ($action === 'getdata') {
    header('Content-Type: application/json');
    try {
        $conn = local_microlearning_get_sqlserver_connection();
        if (!$conn) throw new Exception('PostgreSQL connection failed');

        $data = [];

        if ($isteacher) {
            // 0. Fetch available weeks for the filter
            $stmt = $conn->prepare("
                SELECT DISTINCT year, week_of_year 
                FROM datamart.fact_risk_student_weekly 
                WHERE CAST(course_key AS VARCHAR) = ? OR ? = '1'
                ORDER BY year DESC, week_of_year DESC 
                LIMIT 20
            ");
            $stmt->execute([$courseid, $courseid]);
            $data['available_weeks'] = $stmt->fetchAll(PDO::FETCH_ASSOC);

            // Determine specific week filter
            $week_filter = "";
            $week_params = [$courseid, $courseid];
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
                    WHERE (CAST(course_key AS VARCHAR) = ? OR ? = '1')";
            
            if ($week === 'latest') {
                $sql .= " AND (year, week_of_year) IN (SELECT year, week_of_year FROM datamart.fact_risk_student_weekly WHERE CAST(course_key AS VARCHAR) = ? OR ? = '1' ORDER BY year DESC, week_of_year DESC LIMIT 1)";
                $stmt = $conn->prepare($sql);
                $stmt->execute([$courseid, $courseid, $courseid, $courseid]);
            } else if ($week === 'all') {
                $stmt = $conn->prepare($sql);
                $stmt->execute([$courseid, $courseid]);
            } else {
                $sql .= $week_filter;
                $stmt = $conn->prepare($sql);
                $stmt->execute($week_params);
            }
            $data['global_stats'] = $stmt->fetch(PDO::FETCH_ASSOC);

            // 2. Class Trends (no change, always show history)
            $stmt = $conn->prepare("
                SELECT week_of_year, avg_engagement_score, active_student_count, medium_engagement_count, low_engagement_count, passive_student_count
                FROM datamart.fact_class_engagement_distribution
                WHERE CAST(course_key AS VARCHAR) = ? OR ? = '1'
                ORDER BY year DESC, week_of_year DESC LIMIT 12
            ");
            $stmt->execute([$courseid, $courseid]);
            $data['class_trends'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC));

            // 3. Student Performance List
            $sql = "SELECT a.actor_name, f.student_key, f.engagement_score, f.risk_level, f.dropout_probability_pct, l.current_progress_pct, l.last_activity_date
                    FROM (";
            
            if ($week === 'latest' || $week === 'all') {
                $sql .= "SELECT DISTINCT ON (student_key) student_key, course_key, engagement_score, risk_level, dropout_probability_pct, year, week_of_year
                         FROM datamart.fact_risk_student_weekly
                         WHERE CAST(course_key AS VARCHAR) = ? OR ? = '1'
                         ORDER BY student_key, year DESC, week_of_year DESC";
                $student_params = [$courseid, $courseid];
            } else {
                $sql .= "SELECT student_key, course_key, engagement_score, risk_level, dropout_probability_pct, year, week_of_year
                         FROM datamart.fact_risk_student_weekly
                         WHERE (CAST(course_key AS VARCHAR) = ? OR ? = '1') " . $week_filter;
                $student_params = $week_params;
            }
            
            $sql .= ") f
                    JOIN datamart.dim_actor a ON f.student_key = a.actor_id
                    LEFT JOIN datamart.fact_student_course_lifecycle l ON f.student_key = l.student_key AND CAST(f.course_key AS VARCHAR) = CAST(l.course_key AS VARCHAR)
                    ORDER BY f.dropout_probability_pct DESC LIMIT 20";
            
            $stmt = $conn->prepare($sql);
            $stmt->execute($student_params);
            $data['students'] = $stmt->fetchAll(PDO::FETCH_ASSOC);

            // 4. Behavioral Correlations (fact_behavior_outcome_correlation)
            $stmt = $conn->prepare("
                SELECT avg_time_on_task, avg_final_score, cram_student_count
                FROM datamart.fact_behavior_outcome_correlation
                WHERE CAST(course_key AS VARCHAR) = ? OR ? = '1'
                ORDER BY year DESC, week_of_year DESC LIMIT 1
            ");
            $stmt->execute([$courseid, $courseid]);
            $data['correlation'] = $stmt->fetch(PDO::FETCH_ASSOC);

        } else {
            // Student View
            // 1. My Lifecycle (fact_student_course_lifecycle)
            $stmt = $conn->prepare("
                SELECT current_progress_pct, completed_module_count, current_status, days_since_last_activity, last_activity_date
                FROM datamart.fact_student_course_lifecycle
                WHERE student_key = ? AND (CAST(course_key AS VARCHAR) = ? OR ? = '1')
                LIMIT 1
            ");
            $stmt->execute([(string)$currentuserid, $courseid, $courseid]);
            $data['my_lifecycle'] = $stmt->fetch(PDO::FETCH_ASSOC);

            // 2. My Engagement History (fact_daily_student_engagement)
            $stmt = $conn->prepare("
                SELECT t.date, t.day_of_week, f.total_active_minutes, f.engagement_score
                FROM datamart.fact_daily_student_engagement f
                JOIN datamart.dim_time t ON f.date_key = t.time_id
                WHERE f.student_key = ? AND (CAST(f.course_key AS VARCHAR) = ? OR ? = '1')
                ORDER BY t.year DESC, t.month DESC, t.date DESC LIMIT 14
            ");
            $stmt->execute([(string)$currentuserid, $courseid, $courseid]);
            $data['my_daily'] = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC));
        }

        echo json_encode($data);
    } catch (Exception $e) {
        echo json_encode(['error' => $e->getMessage()]);
    }
    exit;
}

// Fetch course list for selector
$courses = [];
try {
    $conn = local_microlearning_get_sqlserver_connection();
    if ($conn) {
        $stmt = $conn->query("SELECT course_key, course_name FROM datamart.dim_course WHERE CAST(course_key AS VARCHAR) != '1' ORDER BY course_name ASC");
        $courses = $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
} catch (Exception $e) {}

echo $OUTPUT->header();
?>

<!-- Style & Assets -->
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/apexcharts"></script>

<style>
    body { font-family: 'Inter', sans-serif; background: #f8fafc; }
    .card { background: white; border: 1px solid #e2e8f0; border-radius: 1.5rem; padding: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    .stat-val { font-size: 1.875rem; font-weight: 800; color: #1e293b; }
    .stat-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; }
</style>

<div class="max-w-[1600px] mx-auto p-6 space-y-8">
    <!-- Header -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
            <h1 class="text-3xl font-extrabold text-slate-900">Datamart <span class="text-indigo-600">Analytics</span></h1>
            <p class="text-slate-500">Visualizing raw learning metrics from the data warehouse.</p>
        </div>
        <div class="flex flex-wrap items-center gap-3 bg-white p-2 rounded-2xl border border-slate-200">
            <div class="flex flex-col px-2 border-r border-slate-100">
                <span class="text-[10px] font-bold text-slate-400 uppercase">Khóa học</span>
                <select id="course-selector" class="bg-transparent font-bold text-slate-700 focus:outline-none cursor-pointer">
                    <option value="1">Tất cả khóa học</option>
                    <?php foreach ($courses as $c): ?>
                        <option value="<?= s($c['course_key']) ?>" <?= $courseid === (string)$c['course_key'] ? 'selected' : '' ?>><?= s($c['course_name']) ?></option>
                    <?php endforeach; ?>
                </select>
            </div>
            
            <?php if ($isteacher): ?>
            <div class="flex flex-col px-2">
                <span class="text-[10px] font-bold text-slate-400 uppercase">Thời gian</span>
                <select id="week-selector" class="bg-transparent font-bold text-slate-700 focus:outline-none cursor-pointer">
                    <option value="latest">Tuần mới nhất</option>
                    <option value="all">Tất cả thời gian</option>
                </select>
            </div>
            <?php endif; ?>

            <button onclick="fetchData()" class="bg-indigo-600 text-white p-2 rounded-xl hover:bg-indigo-700 transition-all shadow-lg shadow-indigo-100 active:scale-95 ml-2">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
            </button>
        </div>
    </div>

    <!-- Metrics Grid -->
    <div id="metric-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6"></div>

    <!-- Dashboard Content -->
    <div id="dashboard-content" class="grid grid-cols-1 lg:grid-cols-12 gap-8"></div>
</div>

<script>
    const isTeacher = <?= $isteacher ? 'true' : 'false' ?>;
    let charts = {};

    async function fetchData() {
        const courseId = document.getElementById('course-selector').value;
        const weekSelector = document.getElementById('week-selector');
        const week = weekSelector ? weekSelector.value : 'latest';

        const resp = await fetch(`dashboard.php?action=getdata&courseid=${courseId}&week=${week}`);
        const data = await resp.json();
        if (data.error) return console.error(data.error);

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
    }

    function renderMetrics(data) {
        const grid = document.getElementById('metric-grid');
        grid.innerHTML = '';
        
        let metrics = [];
        if (isTeacher && data.global_stats) {
            metrics = [
                { 
                    label: 'Tổng số học sinh', 
                    val: data.global_stats.total_students, 
                    sub: 'Người dùng định danh',
                    tip: 'Tổng số học viên duy nhất tham gia. Giúp xác định quy mô lớp học để điều chỉnh giáo trình và khối lượng hỗ trợ phù hợp.'
                },
                { 
                    label: 'Điểm tương tác TB', 
                    val: Math.round(data.global_stats.avg_engagement), 
                    sub: 'Điểm trung bình tuần',
                    tip: 'Cách tính (max 100đ): Phút học (60đ) + Truy cập tài liệu (20đ) + Làm bài (20đ). Chỉ số này phản ánh độ nhiệt huyết của lớp; mức lý tưởng là >50đ.'
                },
                { 
                    label: 'Điểm rủi ro TB', 
                    val: Math.round(data.global_stats.avg_risk), 
                    sub: 'Chỉ số dự báo',
                    tip: 'Xác suất bỏ học dự báo (0-100%). Được tính toán dựa trên sự sụt giảm tần suất đăng nhập và tiến độ làm bài. >50% cần can thiệp ngay.'
                },
                { 
                    label: 'Học dồn cuối kỳ', 
                    val: data.correlation?.cram_student_count || 0, 
                    sub: 'SV có hành vi học dồn',
                    tip: 'Số SV có hành vi học dồn (Cramming): Học rất ít ở đầu kỳ nhưng tăng đột biến >300% thời gian ở cuối kỳ. Đây là nhóm học để đối phó, kiến thức khó bền vững.'
                }
            ];
        } else if (data.my_lifecycle) {
            metrics = [
                { 
                    label: 'Tiến độ của tôi', 
                    val: data.my_lifecycle.current_progress_pct + '%', 
                    sub: data.my_lifecycle.completed_module_count + ' học phần',
                    tip: 'Phần trăm bài học đã hoàn thành. Hệ thống tính dựa trên số lượng module/hoạt động. Bạn nên duy trì mức >10%/tuần để về đích đúng hạn.'
                },
                { 
                    label: 'Trạng thái hiện tại', 
                    val: data.my_lifecycle.current_status, 
                    sub: 'Vòng đời học tập',
                    tip: 'Xếp loại dựa trên sự chuyên cần. Tích cực (học đều), Chậm trễ (vắng học > 3 ngày), Rủi ro (vắng học > 7 ngày).'
                },
                { 
                    label: 'Hoạt động cuối', 
                    val: data.my_lifecycle.days_since_last_activity + ' ngày trước', 
                    sub: data.my_lifecycle.last_activity_date,
                    tip: 'Thời điểm gần nhất bạn vào học. Duy trì khoảng cách vắng học dưới 48h để giữ thói quen học tập tốt nhất.'
                },
                { 
                    label: 'Tương tác', 
                    val: data.my_daily.at(-1)?.engagement_score || 0, 
                    sub: 'Điểm tương tác gần nhất',
                    tip: 'Điểm nỗ lực cá nhân trong ngày gần nhất. Mục tiêu đạt trên 50đ mỗi ngày học giúp bạn ghi nhớ kiến thức lâu hơn.'
                }
            ];
        }

        metrics.forEach(m => {
            grid.innerHTML += `
                <div class="card relative group">
                    <div class="stat-label">${m.label}</div>
                    <div class="stat-val">${m.val}</div>
                    <div class="text-[10px] font-bold text-slate-400 mt-1 uppercase">${m.sub}</div>
                    ${m.tip ? `
                        <div class="absolute top-4 right-4 cursor-help opacity-40 group-hover:opacity-100 transition-opacity" title="${m.tip}">
                            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </div>
                    ` : ''}
                </div>
            `;
        });
    }

    function renderTeacher(data) {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="lg:col-span-8 space-y-8">
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                        Xu hướng tương tác của lớp
                        <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Theo dõi sự thay đổi theo tuần. Nếu đồ thị đi xuống, có thể nội dung tuần đó quá khó hoặc sinh viên đang mất động lực.">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </h3>
                    <div id="trend-chart" class="h-[300px]"></div>
                </div>
                <div class="card overflow-hidden">
                    <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                        Chi tiết hiệu suất sinh viên
                        <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Bảng chi tiết giúp định danh chính xác sinh viên nào đang tụt lại để giảng viên có thể gửi email nhắc nhở kịp thời.">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </h3>
                    <div class="overflow-x-auto">
                        <table class="w-full text-left">
                            <thead>
                                <tr class="text-[10px] font-bold text-slate-400 border-b border-slate-100 uppercase">
                                    <th class="pb-4" title="Tên học viên ghi nhận từ Moodle.">Sinh viên</th>
                                    <th class="pb-4" title="Tỷ lệ hoàn thành so với tổng số hoạt động trong khóa học.">Tiến độ</th>
                                    <th class="pb-4" title="Chỉ số dự báo bỏ học. > 50% là mức nguy hiểm, cần can thiệp.">Rủi ro %</th>
                                    <th class="pb-4" title="Tổng điểm tương tác tích lũy (bao gồm học tập, xem tài liệu và làm bài).">Điểm T.Tác</th>
                                    <th class="pb-4" title="Ngày cuối cùng sinh viên có hành vi click/hoạt động trên khóa học.">H.Động cuối</th>
                                </tr>
                            </thead>
                            <tbody class="divide-y divide-slate-50">
                                ${data.students.map(s => `
                                    <tr class="text-sm">
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
                                        <td class="py-4 font-mono text-xs">${s.engagement_score}</td>
                                        <td class="py-4 text-[10px] font-bold text-slate-400">${s.last_activity_date}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            <div class="lg:col-span-4 space-y-8">
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                        Phân loại tương tác
                        <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Chia SV thành 4 nhóm: Tích cực (>70đ), TB (40-70đ), Thấp (10-40đ), Thụ động (<10đ). Giúp giảng viên có chiến lược hỗ trợ riêng biệt cho từng nhóm.">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </h3>
                    <div id="mix-chart"></div>
                </div>
                <div class="card border-indigo-100 shadow-indigo-100/50 shadow-xl border-l-4 border-l-indigo-600">
                    <h3 class="text-lg font-bold mb-4 flex items-center gap-2 text-indigo-900">
                        Mối tương quan hành vi
                        <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Phân tích: Nếu SV dành nhiều thời gian học nhưng điểm thấp, có thể SV đang gặp khó khăn trong việc tiếp thu. Nếu cả hai đều cao biểu thị việc học đang rất hiệu quả.">
                            <svg class="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </h3>
                    <div class="space-y-4 text-sm">
                        <p class="text-slate-500 font-medium">Dữ liệu phản ánh mối liên hệ giữa thời gian học và điểm số cuối cùng.</p>
                        <div class="pt-4 border-t border-slate-100 flex justify-between items-center group">
                            <div class="text-[10px] font-black uppercase tracking-widest text-slate-400">Thời gian học TB / Tuần</div>
                            <div class="text-xl font-black text-indigo-600">${Math.round(data.correlation?.avg_time_on_task || 0)} <span class="text-xs text-slate-400">phút</span></div>
                        </div>
                        <div class="pt-2 flex justify-between items-center group">
                            <div class="text-[10px] font-black uppercase tracking-widest text-slate-400">Điểm số TB</div>
                            <div class="text-2xl font-black text-indigo-600">${data.correlation?.avg_final_score || 0}%</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        new ApexCharts(document.querySelector("#trend-chart"), {
            series: [{ name: 'Điểm tương tác TB', data: data.class_trends.map(t => t.avg_engagement_score) }],
            chart: { type: 'area', height: 300, toolbar: { show: false } },
            stroke: { curve: 'smooth', width: 3 },
            xaxis: { categories: data.class_trends.map(t => 'Tuần ' + t.week_of_year) },
            colors: ['#6366f1']
        }).render();

        new ApexCharts(document.querySelector("#mix-chart"), {
            series: [
                data.class_trends.at(-1)?.active_student_count || 0,
                data.class_trends.at(-1)?.medium_engagement_count || 0,
                data.class_trends.at(-1)?.low_engagement_count || 0,
                data.class_trends.at(-1)?.passive_student_count || 0
            ],
            chart: { type: 'donut', height: 280 },
            labels: ['Tích cực', 'Trung bình', 'Thấp', 'Thụ động'],
            colors: ['#6366f1', '#8b5cf6', '#f43f5e', '#e2e8f0'],
            legend: { position: 'bottom' }
        }).render();
    }

    function renderStudent(data) {
        const content = document.getElementById('dashboard-content');
        content.innerHTML = `
            <div class="lg:col-span-12 space-y-8">
                <div class="card">
                    <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                        Lịch sử tương tác của tôi
                        <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Theo dõi biến động điểm tương tác cá nhân của bạn theo thời gian học tập.">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                        </span>
                    </h3>
                    <div id="engagement-chart" class="h-[350px]"></div>
                </div>
            </div>
            <div class="lg:col-span-4 card">
                <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                    Thời gian học 7 ngày qua
                    <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Thống kê tổng số phút bạn đã thực sự thao tác và học tập trong một tuần qua.">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </span>
                </h3>
                <div id="minutes-chart"></div>
            </div>
            <div class="lg:col-span-8 card">
                <h3 class="text-lg font-bold mb-6 text-slate-800 flex items-center gap-2">
                    Nhật ký hoạt động
                    <span class="cursor-help opacity-40 hover:opacity-100 transition-opacity" title="Nhật ký lưu trữ chi tiết các phiên học tập gần nhất của bạn trên hệ thống.">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
                    </span>
                </h3>
                <div class="space-y-3">
                    ${data.my_daily.map(d => `
                        <div class="flex items-center justify-between p-3 bg-slate-50 rounded-xl border border-slate-100 group hover:border-indigo-200 transition-colors">
                            <div>
                                <div class="text-xs font-bold text-slate-700">${d.day_of_week}, ${d.date}</div>
                                <div class="text-[10px] font-medium text-slate-400 group-hover:text-indigo-400 transition-colors">Điểm số: <span class="font-bold">${d.engagement_score}</span></div>
                            </div>
                            <div class="text-sm font-black text-indigo-600">${d.total_active_minutes} phút</div>
                        </div>
                    `).reverse().join('')}
                </div>
                <div class="mt-6 p-4 bg-indigo-50 border border-indigo-100 rounded-2xl text-[11px] text-indigo-600 leading-relaxed font-medium">
                    <p class="font-bold mb-1">💡 Giải thích về Điểm tương tác:</p>
                    Điểm số này phản ánh mức độ tích cực của bạn. Tối đa 100 điểm/ngày, bao gồm:<br>
                    - Thời gian học: 1 điểm cho mỗi phút (tối đa 60).<br>
                    - Tài liệu: 1 điểm cho mỗi lần xem (tối đa 20).<br>
                    - Làm bài: 2 điểm cho mỗi lần làm bài tập/quiz (tối đa 20).
                </div>
            </div>
        `;

        new ApexCharts(document.querySelector("#engagement-chart"), {
            series: [{ name: 'Điểm tương tác', data: data.my_daily.map(d => d.engagement_score) }],
            chart: { type: 'area', height: 350, toolbar: { show: false } },
            stroke: { curve: 'smooth' },
            xaxis: { categories: data.my_daily.map(d => d.date) },
            colors: ['#6366f1']
        }).render();

        new ApexCharts(document.querySelector("#minutes-chart"), {
            series: [{ name: 'Số phút', data: data.my_daily.slice(-7).map(d => parseInt(d.total_active_minutes)) }],
            chart: { type: 'bar', height: 250, toolbar: { show: false } },
            plotOptions: { bar: { borderRadius: 8, columnWidth: '50%' } },
            xaxis: { categories: data.my_daily.slice(-7).map(d => d.day_of_week.substring(0,3)) },
            colors: ['#8b5cf6']
        }).render();
    }

    document.addEventListener('DOMContentLoaded', fetchData);
    document.getElementById('course-selector').addEventListener('change', fetchData);
</script>

<?php echo $OUTPUT->footer(); ?>
