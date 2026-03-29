from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db

class LoadFactStudentDeadlineProximity:
    def __init__(self):
        self.dm = "datamart"
        self.dw = "datawarehouse"
        self.moodle_db = moodle_db

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_deadline_proximity;")

        # 1. Fetch Quiz Deadlines
        moodle_quiz_query = "SELECT id, course, timeclose as deadline FROM mdl_quiz WHERE timeclose > 0"
        quizzes = self.moodle_db.inquiry_query(moodle_quiz_query)
        
        for q in quizzes:
            deadline_ts = q['deadline']
            insert_query = f"""
                INSERT INTO {self.dm}.fact_student_deadline_proximity (
                    student_key, course_key, resource_key, 
                    deadline_date, first_attempt_date, 
                    pressure_level
                )
                SELECT 
                    a.actor_id, CAST(c.course_id AS VARCHAR), CAST(a.quiz_id AS VARCHAR),
                    TO_TIMESTAMP(%s), MIN(a.start_time),
                    CASE 
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - MIN(a.start_time)))/3600 > 48 THEN 'Safe'
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s) - MIN(a.start_time)))/3600 > 12 THEN 'Warning'
                        ELSE 'Critical'
                    END
                FROM {self.dw}.fact_quiz a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE a.quiz_id = %s
                GROUP BY a.actor_id, c.course_id, a.quiz_id;
            """
            db.execute_query(insert_query, (deadline_ts, deadline_ts, deadline_ts, q['id']))

        # 2. Fetch Assignment Deadlines
        moodle_assign_query = """
            SELECT a.id, cm.id as cmid, a.course, a.duedate as deadline 
            FROM mdl_assign a
            JOIN mdl_course_modules cm ON a.id = cm.instance
            JOIN mdl_modules m ON cm.module = m.id
            WHERE a.duedate > 0 AND m.name = 'assign'
        """
        assigns = self.moodle_db.inquiry_query(moodle_assign_query)
        
        for a in assigns:
            deadline_ts = a['deadline']
            # For assignments, we'll check first interaction in fact_activity (using regex to find numerical ID which usually is cmid)
            insert_query = f"""
                INSERT INTO {self.dm}.fact_student_deadline_proximity (
                    student_key, course_key, resource_key, 
                    deadline_date, first_attempt_date, 
                    pressure_level
                )
                SELECT 
                    a.actor_id, CAST(c.course_id AS VARCHAR), %s,
                    TO_TIMESTAMP(%s)::TIMESTAMP, 
                    CAST(MIN(t.year || '-' || LPAD(t.month::text, 2, '0') || '-' || LPAD(t.date::text, 2, '0') || ' 00:00:00') AS TIMESTAMP),
                    CASE 
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s)::TIMESTAMP - CAST(MIN(t.year || '-' || LPAD(t.month::text, 2, '0') || '-' || LPAD(t.date::text, 2, '0') || ' 00:00:00') AS TIMESTAMP)))/3600 > 48 THEN 'Safe'
                        WHEN EXTRACT(EPOCH FROM (TO_TIMESTAMP(%s)::TIMESTAMP - CAST(MIN(t.year || '-' || LPAD(t.month::text, 2, '0') || '-' || LPAD(t.date::text, 2, '0') || ' 00:00:00') AS TIMESTAMP)))/3600 > 12 THEN 'Warning'
                        ELSE 'Critical'
                    END
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                JOIN {self.dw}.dim_time t ON a.time_id = t.time_id
                WHERE (a.activity_id LIKE '%%assign%%' AND regexp_replace(a.activity_id, '[^0-9]', '', 'g') = %s)
                GROUP BY a.actor_id, c.course_id;
            """
            db.execute_query(insert_query, (str(a['cmid']), deadline_ts, deadline_ts, deadline_ts, str(a['cmid'])))
            
        print("Successfully loaded FactStudentDeadlineProximity (Quizzes & Assignments).")
