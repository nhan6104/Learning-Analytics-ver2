from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db
from datetime import datetime

class LoadFactStudentCourseLifeCycle:
    def __init__(self):
        self.datamart_name = "datamart"
        self.moodle_db = moodle_db

    def load(self):
        # 1. Fetch Course metadata
        courses_query = f"SELECT course_key, total_modules FROM {self.datamart_name}.dim_course"
        courses = db.execute_query(courses_query)
        
        # 2. Process each course
        for course in courses:
            course_key = course[0]
            total_modules = course[1]
            if not total_modules or total_modules == 0:
                continue

            # Fetch completion data from Moodle for this course
            # We want all completions ordered by time to identify milestones
            moodle_query = """
                SELECT 
                    cmc.userid as student_key,
                    cmc.timemodified as completion_time
                FROM mdl_course_modules_completion cmc
                JOIN mdl_course_modules cm ON cmc.coursemoduleid = cm.id
                WHERE cm.course = %s AND cmc.completionstate = 1
                ORDER BY cmc.userid, cmc.timemodified ASC
            """
            completions = self.moodle_db.inquiry_query(moodle_query, (course_key,))
            
            # Group by student
            student_completions = {}
            for row in completions:
                s_key = str(row['student_key'])
                if s_key not in student_completions:
                    student_completions[s_key] = []
                student_completions[s_key].append(row['completion_time'])

            # 3. Get last activity info from Datamart
            activity_query = f"""
                SELECT 
                    student_key, 
                    MAX(date_key) as last_date
                FROM {self.datamart_name}.fact_daily_student_engagement
                WHERE course_key = %s
                GROUP BY student_key
            """
            # Need to fix: date_key in our case is time_id (e.g. M202622391)
            # This is hard to compare as a date directly. 
            # Better to join with dim_time to get actual date.
            activity_query = f"""
                SELECT 
                    f.student_key, 
                    MAX(CAST(CONCAT(t.year, '-', t.month, '-', t.date) AS DATE)) as last_activity_date
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                WHERE f.course_key = %s
                GROUP BY f.student_key
            """
            recent_activities = db.execute_query(activity_query, (course_key,))
            student_activities = {str(row[0]): row[1] for row in recent_activities}

            # 4. Calculate facts for each student
            # We iterate over students found in completions or activity
            all_students = set(student_completions.keys()) | set(student_activities.keys())
            
            records = []
            for s_key in all_students:
                s_completions = student_completions.get(s_key, [])
                comp_count = len(s_completions)
                progress_pct = int((comp_count / total_modules) * 100)
                
                # Milestones
                m25 = datetime.fromtimestamp(s_completions[int(total_modules * 0.25) - 1]).date() if comp_count >= total_modules * 0.25 else None
                m50 = datetime.fromtimestamp(s_completions[int(total_modules * 0.50) - 1]).date() if comp_count >= total_modules * 0.50 else None
                m75 = datetime.fromtimestamp(s_completions[int(total_modules * 0.75) - 1]).date() if comp_count >= total_modules * 0.75 else None
                comp_date = datetime.fromtimestamp(s_completions[-1]).date() if progress_pct >= 100 else None
                
                last_act = student_activities.get(s_key)
                days_since = (datetime.now().date() - last_act).days if last_act else None
                
                status = "Active"
                dropout_date = None
                if progress_pct >= 100:
                    status = "Completed"
                elif days_since and days_since > 30:
                    status = "Dropout"
                    dropout_date = last_act # Approximation

                records.append((
                    s_key, int(course_key), m25, m50, m75, comp_date,
                    progress_pct, comp_count, dropout_date, total_modules,
                    status, days_since, last_act
                ))

            # 5. Insert into Datamart
            if records:
                insert_query = f"""
                    INSERT INTO {self.datamart_name}.fact_student_course_lifecycle (
                        student_key, course_key, milestone_25_date, milestone_50_date, milestone_75_date,
                        completion_date, current_progress_pct, completed_module_count, dropout_date,
                        total_module_count, current_status, days_since_last_activity, last_activity_date
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (student_key, course_key) DO UPDATE SET
                        milestone_25_date = EXCLUDED.milestone_25_date,
                        milestone_50_date = EXCLUDED.milestone_50_date,
                        milestone_75_date = EXCLUDED.milestone_75_date,
                        completion_date = EXCLUDED.completion_date,
                        current_progress_pct = EXCLUDED.current_progress_pct,
                        completed_module_count = EXCLUDED.completed_module_count,
                        dropout_date = EXCLUDED.dropout_date,
                        total_module_count = EXCLUDED.total_module_count,
                        current_status = EXCLUDED.current_status,
                        days_since_last_activity = EXCLUDED.days_since_last_activity,
                        last_activity_date = EXCLUDED.last_activity_date
                """
                # We need a unique constraint for ON CONFLICT to work
                # Let's check if the table has one
                for rec in records:
                    db.execute_query(insert_query, rec)