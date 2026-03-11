# Dashboard Queries Documentation

This document describes the key SQL queries used to drive the Learning Analytics Dashboard, separated by user persona.

---

## 👨‍🏫 1. Teacher Dashboard (Class Overview)

Focus: Identifying at-risk students, class-level progress, and overall participation.

### Query T1: At-Risk Student List
Lists students who need immediate attention.
```sql
SELECT 
    student_key, course_key, dropout_probability_pct, risk_level, engagement_score
FROM datamart.fact_risk_student_weekly
WHERE risk_level = 'High'
ORDER BY dropout_probability_pct DESC;
```

### Query T2: Class Engagement Distribution
Shows the mix of student types in a course for a specific week.
```sql
SELECT 
    course_key, week_of_year,
    low_engagement_count, medium_engagement_count, high_engagement_count, passive_student_count
FROM datamart.fact_class_engagement_distribution
WHERE course_key = :course_id;
```

### Query T3: Inactivity Warning
Students who are active in the course but haven't interacted in 7+ days.
```sql
SELECT student_key, course_key, days_since_last_activity, last_activity_date
FROM datamart.fact_student_course_lifecycle
WHERE days_since_last_activity > 7 AND current_status = 'Active';
```

---

## 🎓 2. Student Dashboard (Personal View)

Focus: Individual performance, progress tracking, and comparison with class average.

### Query S1: My Progress vs. Class Average
Helps students visualize where they stand compared to their peers.
```sql
SELECT 
    s.course_key,
    s.current_progress_pct as my_progress,
    (SELECT AVG(current_progress_pct) 
     FROM datamart.fact_student_course_lifecycle 
     WHERE course_key = s.course_key) as class_avg_progress
FROM datamart.fact_student_course_lifecycle s
WHERE s.student_key = :student_id AND s.course_key = :course_id;
```

### Query S2: My Weekly Engagement Score
Shows the student's personal engagement trend.
```sql
SELECT week, engagement_score, risk_level
FROM datamart.fact_risk_student_weekly
WHERE student_key = :student_id AND course_key = :course_id
ORDER BY week ASC;
```

### Query S3: Daily Study Habits (Heatmap)
Helps students identify their most productive days.
```sql
SELECT 
    t.day_of_week,
    SUM(f.total_active_minutes) as minutes_spent
FROM datamart.fact_daily_student_engagement f
JOIN datamart.dim_time t ON f.date_key = t.time_id
WHERE f.student_key = :student_id
GROUP BY t.day_of_week;
```

### Query S4: Course Milestones Status
Check which milestones have been achieved.
```sql
SELECT 
    milestone_25_date, milestone_50_date, milestone_75_date, completion_date,
    current_progress_pct, completed_module_count, total_module_count
FROM datamart.fact_student_course_lifecycle
WHERE student_key = :student_id AND course_key = :course_id;
```

