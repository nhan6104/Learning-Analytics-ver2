"""
Load Fact Student Course Lifecycle V2

This V2 loader implements safe milestone calculation with bounds checking.

Fixes Bug 2: Milestone Calculation
- Adds bounds checking before accessing completion list indices
- Returns NULL for milestones not yet reached
- Prevents IndexError crashes
"""

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
            
            # Handle edge cases
            if not total_modules or total_modules == 0:
                continue

            # Fetch completion data from Moodle for this course
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
                    f.student_key, 
                    MAX(CAST(CONCAT(t.year, '-', LPAD(t.month::TEXT, 2, '0'), '-', LPAD(t.date::TEXT, 2, '0')) AS DATE)) as last_activity_date
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                WHERE f.course_key = %s
                GROUP BY f.student_key
            """
            recent_activities = db.execute_query(activity_query, (course_key,))
            student_activities = {str(row[0]): row[1] for row in recent_activities}

            # 4. Calculate facts for each student
            all_students = set(student_completions.keys()) | set(student_activities.keys())
            
            records = []
            for s_key in all_students:
                s_completions = student_completions.get(s_key, [])
                comp_count = len(s_completions)
                progress_pct = int((comp_count / total_modules) * 100) if total_modules > 0 else 0
                
                # V2: Safe milestone calculation with bounds checking
                # Calculate milestone indices
                milestone_25_index = int(total_modules * 0.25) - 1 if total_modules > 0 else -1
                milestone_50_index = int(total_modules * 0.50) - 1 if total_modules > 0 else -1
                milestone_75_index = int(total_modules * 0.75) - 1 if total_modules > 0 else -1
                
                # Ensure indices are non-negative
                milestone_25_index = max(0, milestone_25_index)
                milestone_50_index = max(0, milestone_50_index)
                milestone_75_index = max(0, milestone_75_index)
                
                # Safe access with bounds checking
                m25 = None
                if comp_count > milestone_25_index and milestone_25_index >= 0:
                    try:
                        m25 = datetime.fromtimestamp(s_completions[milestone_25_index]).date()
                    except (IndexError, ValueError, OSError) as e:
                        print(f"Warning: Could not calculate 25% milestone for student {s_key}: {e}")
                        m25 = None
                
                m50 = None
                if comp_count > milestone_50_index and milestone_50_index >= 0:
                    try:
                        m50 = datetime.fromtimestamp(s_completions[milestone_50_index]).date()
                    except (IndexError, ValueError, OSError) as e:
                        print(f"Warning: Could not calculate 50% milestone for student {s_key}: {e}")
                        m50 = None
                
                m75 = None
                if comp_count > milestone_75_index and milestone_75_index >= 0:
                    try:
                        m75 = datetime.fromtimestamp(s_completions[milestone_75_index]).date()
                    except (IndexError, ValueError, OSError) as e:
                        print(f"Warning: Could not calculate 75% milestone for student {s_key}: {e}")
                        m75 = None
                
                # Completion date - only if 100% complete
                comp_date = None
                if comp_count >= total_modules and len(s_completions) > 0:
                    try:
                        comp_date = datetime.fromtimestamp(s_completions[-1]).date()
                    except (IndexError, ValueError, OSError) as e:
                        print(f"Warning: Could not calculate completion date for student {s_key}: {e}")
                        comp_date = None
                
                # Last activity and days since
                last_act = student_activities.get(s_key)
                days_since = None
                if last_act:
                    try:
                        days_since = (datetime.now().date() - last_act).days
                    except Exception as e:
                        print(f"Warning: Could not calculate days_since for student {s_key}: {e}")
                        days_since = None
                
                # Status determination
                status = "Active"
                dropout_date = None
                if progress_pct >= 100:
                    status = "Completed"
                elif days_since and days_since > 30:
                    status = "Dropout"
                    dropout_date = last_act

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
                for rec in records:
                    try:
                        db.execute_query(insert_query, rec)
                    except Exception as e:
                        print(f"Error inserting record for student {rec[0]}, course {rec[1]}: {e}")
                        continue