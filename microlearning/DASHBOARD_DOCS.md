# Tài liệu Dashboard Learning Analytics

Hệ thống dashboard trực quan hóa dữ liệu học tập từ Datamart (PostgreSQL schema `datamart`).
Có 3 giao diện: **Teacher Dashboard**, **Student Detail**, và **Student Dashboard**.

---

## 1. Teacher Dashboard

Bố cục: 4 thẻ tổng quan ở trên cùng, sau đó cột trái (8/12) và cột phải (4/12).

---

### [Hàng đầu] 4 thẻ tổng quan (Metric Cards)

**Bảng:** `fact_risk_student_weekly`, `fact_behavior_outcome_correlation`

Hiển thị 4 chỉ số tổng hợp toàn khóa học, lọc theo tuần đang chọn.

**Thẻ 1 — Tổng số học sinh**
- Truy vấn: `COUNT(DISTINCT student_key)` từ `fact_risk_student_weekly`
- Ý nghĩa: Số học viên duy nhất có dữ liệu tương tác trong khóa học.

**Thẻ 2 — Điểm tương tác TB**
- Truy vấn: `AVG(engagement_score)` từ `fact_risk_student_weekly`
- Cách tính điểm gốc (daily, tổng hợp lên weekly):
  - Resource Score (0–70đ): tổng tương tác tài liệu, có trọng số chất lượng
    - Deep Dive × 2.0 | Stuck × 1.2 | Skimming × 0.4 | Normal × 1.0
    - Tài liệu bắt buộc (is_mandatory) × 1.3, giới hạn 3 lần/tài liệu
  - Quiz Bonus (0–30đ): score ≥ 9 → +15đ | ≥ 7 → +12đ | ≥ 5 → +8đ | > 0 → +4đ | attempt → +2đ
  - Không tính thời gian (xAPI timestamp không đáng tin cậy)
- Phân loại: Excellent ≥ 80 | Good 60–79 | Warning 40–59 | Critical 1–39 | Passive = 0

**Thẻ 3 — Điểm rủi ro TB**
- Truy vấn: `AVG(risk_score)` từ `fact_risk_student_weekly`
- Công thức risk_score (0–100, đa nhân tố):
  - (100 − engagement) × 0.30 → tương tác thấp (30%)
  - trend_penalty: +25 nếu giảm so tuần trước, −10 nếu tăng >20% (25%)
  - LEAST(20, inactivity_days × 3) → ngày không học (20%)
  - LEAST(15, progress_lag × 0.5) → chậm tiến độ (15%)
  - social_isolation: +10 nếu 0 ngày tương tác, +5 nếu < 3 ngày (10%)
- Phân loại risk_level và dropout_probability_pct:
  - Critical (base_risk > 70) → 85% | High (> 50) → 55% | Medium (> 30) → 25% | Low → 8%

**Thẻ 4 — Học dồn cuối kỳ**
- Truy vấn: `COUNT WHERE behavior_pattern = 'High Cramming'` từ `fact_behavior_outcome_correlation`
- Ý nghĩa: Số học sinh nộp bài trong vòng < 12 giờ trước deadline.

---

### [Cột trái #1] Sức khỏe Module — Treemap

**Bảng:** `fact_student_engagement_depth`, `dim_resource`, `dim_section`

Biểu đồ treemap, mỗi ô là một tài liệu/module, kích thước theo `total_interactions`.
Màu sắc phản ánh tình trạng:
- Đỏ: `stuck_rate > 30%` — nhiều học sinh bị mắc kẹt, cần can thiệp
- Vàng: `skimming_rate > 50%` — học sinh lướt qua, nội dung không thu hút
- Xanh lá: còn lại — học sâu bình thường

Các chỉ số tính:
- `total_interactions`: tổng lượt tương tác với module
- `stuck_rate`: `COUNT(Stuck) / COUNT(*) × 100`
- `skimming_rate`: `COUNT(Skimming) / COUNT(*) × 100`

---

### [Cột trái #2] Luồng học tập — Sankey Flow

**Bảng:** `fact_activity_transitions`, `dim_resource`

Biểu đồ Sankey thể hiện luồng chuyển tiếp giữa các tài liệu.
- Mỗi node là một tài liệu/module
- Độ dày đường nối = `transition_count` (số lần học sinh chuyển từ A sang B)
- Cách tính: dùng `LAG()` window function trên `fact_activity` (datawarehouse) để lấy cặp tài liệu liên tiếp trong cùng session
- Ý nghĩa: Luồng dày → đường học phổ biến. Luồng quay ngược → học sinh xem lại tài liệu cũ.

---

### [Cột trái #3] Các bước chuyển tiếp phổ biến — Bar Chart

**Bảng:** `fact_activity_transitions`, `dim_resource`

Biểu đồ cột ngang, top N cặp chuyển tiếp `from_resource → to_resource` theo `transition_count DESC`.
Cùng nguồn dữ liệu với Sankey nhưng hiển thị dạng bảng xếp hạng để dễ đọc số liệu cụ thể.

---

### [Cột trái #4] Tiến trình tiếp cận học phần — Coverage Funnel

**Bảng:** `fact_student_engagement_depth`, `dim_resource`, `dim_section`

Biểu đồ phễu (funnel/bar), mỗi thanh là một tài liệu, chiều cao = số học sinh đã tương tác.
- Truy vấn: `COUNT(DISTINCT student_key)` group by `resource_name`, `section_name`
- Sắp xếp theo thứ tự module trong khóa học
- Ý nghĩa: Phễu thu hẹp dần là bình thường (drop-off tự nhiên). Nếu một module giữa khóa đột ngột thấp → nội dung có vấn đề.

---

### [Cột trái #5] Độ sâu tương tác — Donut Chart (trái)

**Bảng:** `fact_student_engagement_depth`

Biểu đồ donut, phân bổ 4 loại tương tác toàn lớp:
| Loại | Điều kiện phân loại |
|------|---------------------|
| Deep Dive | 75%–120% median lớp VÀ (hoàn thành HOẶC variety ≥ 3 loại) |
| Stuck | > 120% p75 VÀ chưa hoàn thành VÀ variety ≤ 2 loại |
| Skimming | < 50% median lớp HOẶC < 3 lần tương tác |
| Normal | Còn lại |

`depth_ratio = interaction_count / median_interactions_of_class`

---

### [Cột trái #5] Xu hướng tương tác lớp — Area Chart (phải)

**Bảng:** `fact_class_engagement_distribution`

Biểu đồ area, trục X là tuần (12 tuần gần nhất), trục Y là `avg_engagement_score`.
- Nguồn: tổng hợp từ `fact_risk_student_weekly`, group by `course_key`, `week_of_year`, `year`
- Percentile: `p25_engagement`, `p50_engagement`, `p75_engagement` cũng được lưu nhưng chart này chỉ dùng avg
- Ý nghĩa: Xu hướng đi xuống liên tục → lớp đang mất động lực học.

---

### [Cột trái #6] Xu hướng Học dồn — Area Chart

**Bảng:** `fact_behavior_outcome_correlation`

Biểu đồ area, trục X là `behavior_pattern`, trục Y là số học sinh (`cram_student_count`).
- Truy vấn: `GROUP BY behavior_pattern, COUNT(*)`
- Phân loại hành vi dựa trên `avg_hours_before_deadline`:
  - High Cramming: nộp bài < 12h trước deadline, hệ số tương quan −0.7 (quiz < 60%) hoặc −0.3
  - Moderate Cramming: 12–48h trước deadline, hệ số −0.2
  - Planned: > 48h trước deadline, hệ số +0.6 (quiz ≥ 80%) hoặc +0.3

---

### [Cột trái #7] Chi tiết hiệu suất sinh viên — Bảng

**Bảng:** `fact_risk_student_weekly`, `dim_actor`, `fact_student_course_lifecycle`

Bảng danh sách học sinh, sắp xếp theo `dropout_probability_pct DESC` (nguy cơ cao nhất lên đầu).
Các cột: Tên sinh viên | Tiến độ (%) | Rủi ro % | Điểm tương tác | Hoạt động cuối.
Click vào hàng → chuyển sang trang Student Detail.

---

### [Cột phải #1] Phân loại tương tác — Donut Chart

**Bảng:** `fact_class_engagement_distribution`

Biểu đồ donut, lấy dữ liệu tuần mới nhất trong `class_trends`:
- Tích cực: `active_student_count` (engagement ≥ 70, V1 threshold)
- Trung bình: `medium_engagement_count` (40–69)
- Thấp: `low_engagement_count` (1–39)
- Thụ động: `passive_student_count` (= 0)

---

### [Cột phải #2] Phân bổ Áp lực Deadline — Pie Chart

**Bảng:** `fact_student_deadline_proximity`

Biểu đồ pie, phân bổ `pressure_level` toàn lớp:
| Mức | Điều kiện |
|-----|-----------|
| Completed | is_completed = TRUE |
| Safe | > 48h trước deadline |
| Warning | 24–48h trước deadline |
| Critical | 0–24h trước deadline |
| Overdue | Đã qua deadline |

---

### [Cột phải #3] Mối tương quan hành vi — Card thông tin

**Bảng:** `fact_behavior_outcome_correlation`

Card tĩnh hiển thị 1 chỉ số:
- **Điểm số TB:** `AVG(correlated_quiz_score)` — điểm quiz trung bình của tất cả học sinh trong khóa (làm tròn, đơn vị %)
- `correlated_quiz_score` được tính từ `fact_quiz` (datawarehouse): `AVG(score × 10)` để quy về thang 100

---

## 2. Student Detail (`student_detail.php`)

Trang drilldown cá nhân, chỉ giáo viên truy cập. Bố cục tuyến tính từ trên xuống.

---

### [Hàng đầu] 4 thẻ tổng quan cá nhân

**Bảng:** `fact_risk_student_weekly`, `fact_student_course_lifecycle`

| Thẻ | Cột | Bảng |
|-----|-----|------|
| Engagement Score | `engagement_score` (tuần mới nhất) | `fact_risk_student_weekly` |
| Risk Level | `risk_level`, `dropout_probability_pct` | `fact_risk_student_weekly` |
| Course Progress | `current_progress_pct`, `completed_module_count` | `fact_student_course_lifecycle` |
| Last Activity | `days_since_last_activity`, `last_activity_date` | `fact_student_course_lifecycle` |

`current_status`: Active (đang học) | Completed (100% module) | Dropout (không hoạt động > 30 ngày)

---

### [#1] Xu hướng tương tác — Line Chart so sánh với lớp

**Bảng:** `fact_risk_student_weekly`, `fact_class_engagement_distribution`

Biểu đồ đường kép, 12 tuần gần nhất:
- Đường học sinh: `engagement_score` theo tuần
- Đường lớp: `avg_engagement_score` từ `fact_class_engagement_distribution` cùng tuần
- Ý nghĩa: Học sinh liên tục dưới đường lớp → cần can thiệp.

---

### [#2] Ái lực thời gian — Radar/Bar Chart

**Bảng:** `fact_student_time_affinity`

Biểu đồ radar (hoặc bar nếu ít slot), 4 khung giờ: Morning, Afternoon, Evening, Night.
- `efficiency_index = SUM(engagement_score) / COUNT(DISTINCT date_key)` — điểm TB mỗi phiên học
- `relative_efficiency = efficiency_index / student_avg × 100` — so với TB bản thân
- `is_peak_time`: TRUE cho slot có efficiency cao nhất (ROW_NUMBER = 1)
- Phân loại: Peak Productivity ≥ 120% | Above Average 100–119% | Average 80–99% | Below Average < 80%

---

### [#3] Độ sâu tương tác theo tài liệu — Bar Chart

**Bảng:** `fact_student_engagement_depth`, `dim_resource`

Biểu đồ cột, mỗi cột là một tài liệu, chiều cao = `depth_ratio`.
- Sắp xếp: Stuck → Skimming → Deep Dive → Normal (vấn đề lên trước)
- `depth_ratio = interaction_count / median_interactions_of_class`
  - > 1.0: tương tác nhiều hơn TB lớp
  - < 1.0: tương tác ít hơn TB lớp

---

### [#4] Deadline sắp tới — Danh sách

**Bảng:** `fact_student_deadline_proximity`, `dim_resource`

5 deadline gần nhất còn trong tương lai (`deadline_date > NOW()`), sắp xếp `deadline_date ASC`.
- `hours_before_deadline`: tính từ `NOW()` đến `deadline_date`
- Hiển thị màu theo `pressure_level`: đỏ (Critical) | vàng (Warning) | xanh (Safe/Completed)

---

### [#5] Hoạt động hàng ngày — Bar Chart

**Bảng:** `fact_daily_student_engagement`, `dim_time`

Biểu đồ cột, 90 ngày gần nhất, mỗi cột là một ngày.
- Trục Y: `engagement_score`
- Tooltip: `total_resource_access`, `total_quiz_attempt`
- Khoảng trống dài → giai đoạn bỏ học.

---

### [#6] Luồng chuyển tiếp tài liệu — Sankey/Bar

**Bảng:** `fact_activity_transitions`, `dim_resource`

Top 20 transitions của khóa học, lọc những transition có liên quan đến học sinh (EXISTS trong `fact_daily_student_engagement`). Cho thấy luồng học phổ biến của lớp để giáo viên so sánh với hành vi cá nhân.

---

### [#7] Mốc tiến độ — Timeline

**Bảng:** `fact_student_course_lifecycle`

Timeline 4 mốc:
| Mốc | Điều kiện đạt |
|-----|---------------|
| milestone_25_date | Hoàn thành 25% tổng số module |
| milestone_50_date | Hoàn thành 50% tổng số module |
| milestone_75_date | Hoàn thành 75% tổng số module |
| completion_date | Hoàn thành 100% tổng số module |
| dropout_date | Không hoạt động > 30 ngày (ước tính) |

---

### [#8] So sánh với lớp — Stat Cards

**Bảng:** `fact_risk_student_weekly`, `fact_student_course_lifecycle`

3 chỉ số so sánh:
- `engagement_diff_pct = (student_avg − class_avg) / class_avg × 100`
- `risk_diff_pct = (student_risk − class_risk) / class_risk × 100`
- `progress_diff_pct = (student_progress − class_avg_progress) / class_avg_progress × 100`
- `percentile_rank`: `PERCENT_RANK()` theo `AVG(engagement_score)` toàn lớp
- Cờ cảnh báo: `below_avg_engagement = TRUE` nếu `engagement_diff_pct < −30%`

---

## 3. Student Dashboard (chế độ học sinh)

Học sinh chỉ thấy dữ liệu của chính mình. Bố cục: cột trái (8/12) và cột phải (4/12).

---

### [Hàng đầu] 4 thẻ tổng quan cá nhân

**Bảng:** `fact_student_course_lifecycle`, `fact_daily_student_engagement`

| Thẻ | Dữ liệu |
|-----|---------|
| Tiến độ của tôi | `current_progress_pct`, `completed_module_count` |
| Trạng thái hiện tại | `current_status` (Active / Completed / Dropout) |
| Hoạt động cuối | `days_since_last_activity`, `last_activity_date` |
| Điểm tương tác | `engagement_score` ngày gần nhất từ `fact_daily_student_engagement` |

---

### [Cột trái #1] Lịch sử tương tác của tôi — Area Chart

**Bảng:** `fact_daily_student_engagement`, `dim_time`

Biểu đồ area, trục X là ngày, trục Y là `engagement_score` (AVG theo ngày).
- Mặc định 90 ngày, viewall=1 thì 365 ngày
- Ý nghĩa: Học sinh tự theo dõi nhịp học tập, thấy rõ giai đoạn tích cực và giai đoạn bỏ học.

---

### [Cột trái #2 — trái] Nhịp sinh học học tập — Radar Chart

**Bảng:** `fact_student_time_affinity`

Biểu đồ radar 4 trục (Morning / Afternoon / Evening / Night), giá trị = `efficiency_index`.
- Đỉnh cao nhất = khung giờ học hiệu quả nhất
- Ý nghĩa: Học sinh biết nên sắp xếp bài khó vào khung giờ nào.

---

### [Cột trái #2 — phải] Áp lực Deadline — Danh sách

**Bảng:** `fact_student_deadline_proximity`, `dim_resource`

Danh sách 5 deadline sắp tới, hiển thị dạng card màu:
- Đỏ (Critical): còn < 24h
- Vàng (Warning): còn 24–48h
- Xanh (Safe): còn > 48h

---

### [Cột trái #3] Độ sâu học tập — Bar Chart

**Bảng:** `fact_student_engagement_depth`, `dim_resource`

Biểu đồ cột, top 10 tài liệu theo `depth_ratio DESC`.
Màu phân tán theo loại (distributed colors). Học sinh thấy mình đang học sâu hay lướt qua ở tài liệu nào.

---

### [Cột phải #1] Lịch sử hoạt động 90 ngày — Heatmap

**Bảng:** `fact_daily_student_engagement`, `dim_time`

Heatmap calendar (tương tự GitHub contribution graph), mỗi ô là một ngày.
- Màu đậm = `engagement_score` cao
- Màu nhạt/trắng = không có hoạt động

---

### [Cột phải #2] Nhật ký hoạt động — Danh sách

**Bảng:** `fact_daily_student_engagement`, `dim_time`

8 ngày gần nhất, mỗi dòng hiển thị: ngày trong tuần, ngày tháng, điểm tương tác, số phút học.

---

### [Cột phải #3] Insight hành vi — Card tự động

**Bảng:** `fact_student_time_affinity`, `fact_student_engagement_depth`, `fact_student_deadline_proximity`

Card tự sinh 3 loại insight:
1. Khung giờ hiệu suất cao nhất (từ `fact_student_time_affinity`, sort by `efficiency_index DESC`)
2. Cảnh báo tài liệu đang học lướt (từ `fact_student_engagement_depth WHERE engagement_type = 'Skimming'`)
3. Cảnh báo học dồn: `COUNT WHERE pressure_level = 'Critical' > 0` → hiển thị alert đỏ nhấp nháy

---

## Tóm tắt bảng Datamart

| Bảng | Teacher | Student Detail | Student |
|------|---------|----------------|---------|
| `dim_actor` | Danh sách SV | Xác thực SV | — |
| `dim_course` | Dropdown khóa học | Tên khóa học | Dropdown khóa học |
| `dim_resource` | Transitions, Funnel, Treemap | Depth, Deadlines, Transitions | Depth, Deadlines |
| `dim_section` | Funnel, Treemap | — | — |
| `dim_time` | — | Daily activity | Daily history, Heatmap |
| `fact_daily_student_engagement` | — | Daily activity | History, Heatmap, Log |
| `fact_risk_student_weekly` | Overview cards, Danh sách SV | Trend, Comparison | — |
| `fact_class_engagement_distribution` | Class trends, Phân loại | Class avg comparison | — |
| `fact_student_course_lifecycle` | Progress trong danh sách | Milestones, Overview | Overview cards |
| `fact_behavior_outcome_correlation` | Cram card, Cram chart | — | — |
| `fact_student_engagement_depth` | Depth donut, Funnel, Treemap | Depth bar | Depth bar, Insight |
| `fact_student_deadline_proximity` | Pressure pie | Deadlines | Deadlines, Insight |
| `fact_activity_transitions` | Sankey, Top transitions | Transitions | — |
| `fact_student_time_affinity` | — | Radar chart | Radar chart, Insight |
