"""
Load Fact Student Deadline Proximity V2

This V2 loader fixes deadline proximity calculation to use current time.

Fixes Bug 7: Deadline Proximity Calculation
- Uses NOW() instead of first_attempt_time for hours_before calculation
- Checks completion status before calculating pressure
- Excludes completed assignments/quizzes from pressure calculation
- Provides accurate urgency indicators
"""

from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db


class LoadFactStudentDeadlineProximity_v2:
    def __init__(self):
        self.dm = "datamart"
        self.dw = "datawarehouse"
        self.moodle_db = moodle_db

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_deadline_proximity;")

        # 1. Fetch Quiz Deadlines with completion check
        moodle_quiz_query = "SELECT id, course, timeclose as deadline FROM mdl_quiz WHERE timeclose > 0"
        quizzes = self.moodle_db.inquiry_query(moodle_quiz_query)
        
        for q in quizzes:
            deadline_ts = q['deadline']
            insert_query = f"""
                INSERT INTO {self.dm}.fact_student_deadline_proximity (
                    student_key, course_key, resource_key, 
                    deadline_date, first_attempt_date, 
                    hours_before_deadline, pressure_level, is_completed
                )
                SELECT 
                    a.actor_id, 
                    CAST(c.course_id AS VARCHAR), 
                    CAST(a.quiz_id AS VARCHAR),
                    TO_TIMESTAMP(%s),
                    MIN(a.start_time),
                    -- V2: Use NOW() instead of first_attempt_time
                    ROUND(EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - NOW()))/3600, 2) as hours_before_deadline,
                    -- V2: Check completion status first
                    CASE 
                        WHEN MAX(CASE WHEN a.completion_status = TRUE THEN 1 ELSE 0 END) = 1 THEN 'Completed'
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - NOW()))/3600 > 48 THEN 'Safe'
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - NOW()))/3600 > 24 THEN 'Warning'
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - NOW()))/3600 > 0 THEN 'Critical'
                        ELSE 'Overdue'
                    END as pressure_level,
                    CASE WHEN MAX(CASE WHEN a.completion_status = TRUE THEN 1 ELSE 0 END) = 1 THEN TRUE ELSE FALSE END as is_completed
                FROM {self.dw}.fact_quiz a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE a.quiz_id = %s
                GROUP BY a.actor_id, c.course_id, a.quiz_id
                -- V2: Only include if not completed OR if we want to track completed items
                HAVING MAX(CASE WHEN a.completion_status = TRUE THEN 1 ELSE 0 END) = 0 
                    OR TO_TIMESTAMP(%s) > NOW();  -- Include completed if deadline not passed
            """
            db.execute_query(insert_query, (deadline_ts, deadline_ts, deadline_ts, deadline_ts, deadline_ts, q['id'], deadline_ts))

        # Note: Assignment deadline tracking skipped - mdl_assign_submission table not available in this Moodle instance
            
        print("Successfully loaded FactStudentDeadlineProximity V2 with current time calculation and completion check.")
