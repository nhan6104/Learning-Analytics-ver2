from utils.pgsql_utils import db

class LoadFactStudentRiskWeekly:
    def __init__(self):
        self.datamart_name = "datamart"

    def load(self):
        # Clean up existing data for a full refresh
        delete_query = f"TRUNCATE TABLE {self.datamart_name}.fact_risk_student_weekly;"
        db.execute_query(delete_query)

        # We will aggregate from fact_daily_student_engagement and dim_time
        # to calculate weekly scores.
        # This is a simplified risk calculation logic for demonstration.
        # engagement_score: sum of daily engagement
        # risk_score: arbitrary logic based on low engagement
        # dropout_probability_pct: arbitrary logic mapping from risk_score
        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_risk_student_weekly (
                student_key, course_key, week_of_year, year,
                engagement_score, progress_score, outcome_score,
                risk_score, dropout_probability_pct, risk_level
            )
            WITH DailyAgg AS (
                SELECT
                    f.student_key,
                    f.course_key,
                    t.week as week_of_year,
                    t.year,
                    SUM(f.engagement_score) as weekly_engagement_score,
                    SUM(f.total_quiz_attempt) as weekly_quiz_attempts,
                    SUM(f.total_resource_access) as weekly_resource_access
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                GROUP BY f.student_key, f.course_key, t.week, t.year
            )
            SELECT
                student_key,
                course_key,
                week_of_year,
                year,
                weekly_engagement_score as engagement_score,
                weekly_quiz_attempts * 10 as progress_score, -- mock progress
                weekly_resource_access * 5 as outcome_score, -- mock outcome
                CASE 
                    WHEN weekly_engagement_score < 20 THEN 80
                    WHEN weekly_engagement_score < 50 THEN 50
                    ELSE 10
                END as risk_score,
                CASE 
                    WHEN weekly_engagement_score < 20 THEN 80.0
                    WHEN weekly_engagement_score < 50 THEN 45.5
                    ELSE 5.0
                END as dropout_probability_pct,
                CASE 
                    WHEN weekly_engagement_score < 20 THEN 'High'
                    WHEN weekly_engagement_score < 50 THEN 'Medium'
                    ELSE 'Low'
                END as risk_level
            FROM DailyAgg;
        """
        db.execute_query(insert_query)