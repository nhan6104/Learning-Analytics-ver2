from utils.pgsql_utils import db

class LoadFactStudentTimeAffinity:
    def __init__(self):
        self.dm = "datamart"

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_time_affinity;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_student_time_affinity (
                student_key, course_key, time_slot, 
                efficiency_index, total_engagement_score, session_count
            )
            SELECT 
                f.student_key,
                CAST(f.course_key AS VARCHAR),
                t.time_slot,
                ROUND(CAST(SUM(f.engagement_score) AS NUMERIC) / GREATEST(COUNT(DISTINCT f.date_key), 1), 2) as efficiency_index,
                SUM(f.engagement_score) as total_engagement_score,
                COUNT(DISTINCT f.date_key) as session_count
            FROM {self.dm}.fact_daily_student_engagement f
            JOIN {self.dm}.dim_time t ON f.date_key = t.time_id
            GROUP BY f.student_key, f.course_key, t.time_slot;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactStudentTimeAffinity.")
