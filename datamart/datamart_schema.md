# Datamart Schema Documentation

This document provides a detailed description of the Dimension and Fact tables implemented in the Datamart for the Learning Analytics system.

---

## 🏗️ 1. Dimension Tables (Dim)

Dimension tables contain descriptive attributes (context) used for filtering and grouping metrics.

### 👤 `dim_actor`
Stores information about the participants (students/teachers).
- **actor_id** (VARCHAR): Unique identifier for the person (Primary Key).
- **actor_name** (VARCHAR): Full name of the person.

### 📚 `dim_course`
Stores metadata about the available courses.
- **course_key** (VARCHAR): Unique identifier for the course (Primary Key).
- **course_name** (VARCHAR): Full name of the course.
- **course_level** (VARCHAR): Level of the course (e.g., undergraduate).
- **total_modules** (INT): Total number of activities/modules in the course.

### 📄 `dim_resource`
Stores details about learning materials (files, pages, quizzes).
- **resource_key** (VARCHAR): Unique identifier for the resource (Primary Key).
- **resource_name** (VARCHAR): Name of the material.
- **resource_type** (VARCHAR): Type of resource (e.g., page, forum, quiz).
- **course_key** (VARCHAR): Reference to the course it belongs to.

### 📅 `dim_time`
Standard time dimension for temporal analysis.
- **time_id** (VARCHAR): Unique key for a specific date (Format: [M/A][Year][Month][Day][Slot]).
- **date** (INT): Day of the month.
- **month** (INT): Month of the year.
- **year** (INT): Year.
- **week** (INT): Week number within the year.
- **day_of_week** (VARCHAR): Name of the day (e.g., Monday).
- **time_slot** (VARCHAR): Morning, Afternoon, Evening, or Night.

---

## 📊 2. Fact Tables (Fact)

Fact tables contain quantitative metrics (measurements) and foreign keys to dimension tables.

### 🕒 `fact_daily_student_engagement`
Records daily engagement metrics for each student per course.
- **student_key** (VARCHAR): Reference to actor.
- **course_key** (INT): Reference to course.
- **date_key** (VARCHAR): Reference to time dimension.
- **total_active_minutes** (INT): Total time spent in sessions (calculated from DW session duration).
- **total_resource_access** (INT): Count of materials accessed.
- **total_quiz_attempt** (INT): Count of quiz attempts.
- **engagement_score** (INT): Weighted sum of activity metrics.
- **active_learning_index** (INT): Ratio of interactions to time spent.

### ⚠️ `fact_risk_student_weekly`
Weekly aggregation used for predicting dropout risk.
- **student_key** (VARCHAR): Reference to actor.
- **course_key** (INT): Reference to course.
- **week_of_year** (INT): Week number.
- **year** (INT): Year.
- **engagement_score** (INT): Aggregated daily engagement for the week.
- **progress_score** (INT): Mock score based on quiz completions.
- **outcome_score** (INT): Mock score based on resource access.
- **risk_score** (INT): Calculated risk value (10-80).
- **dropout_probability_pct** (DECIMAL): Probability of dropout (5% - 80%).
- **risk_level** (VARCHAR): High, Medium, or Low.

### 📈 `fact_class_engagement_distribution`
Aggregated class-level metrics for course comparison.
- **course_key** (VARCHAR): Reference to course.
- **week_of_year** (INT): Week number.
- **year** (INT): Year.
- **avg_engagement_score** (DECIMAL): Average score across all students in class.
- **p25/p50/p75_engagement** (INT): Score percentiles for the class.
- **active/passive/medium/low_engagement_count** (INT): Headcount of students in each engagement tier.

### 🔄 `fact_student_course_lifecycle`
Summarizes the student's journey through a specific course.
- **student_key** (VARCHAR): Reference to actor.
- **course_key** (INT): Reference to course.
- **milestone_25/50/75_date** (DATE): Date when student reached completion thresholds.
- **completion_date** (DATE): Date of 100% progress.
- **current_progress_pct** (INT): Percentage of modules completed.
- **completed_module_count** (INT): Number of activities completed.
- **dropout_date** (DATE): Estimated date if status is Dropout.
- **current_status** (VARCHAR): Active, Completed, or Dropout.
- **days_since_last_activity** (INT): Recency check.
- **last_activity_date** (DATE): Date of the most recent interaction.

### 🔗 `fact_behavior_outcome_correlation`
Analyzes patterns between behavior and final performance.
- **course_key** (VARCHAR): Reference to course.
- **week_of_year** (INT): Week number.
- **year** (INT): Year.
- **correlation_time_on_task_pass** (INT): Correlation coefficient for time vs. passing.
- **correlation_active_learning_score** (INT): Correlation coefficient for active learning.
- **correlation_cram_failure** (INT): Correlation between "cramming" behavior and failure.
- **avg_time_on_task** (DECIMAL): Average study time.
- **avg_final_score** (DECIMAL): Average score in evaluations.
- **cram_student_count** (INT): Number of students identified as "crammers".
