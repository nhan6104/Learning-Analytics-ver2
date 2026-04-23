from utils.pgsql_utils import db

class LoadFactClassEngagementDistribution:
    def __init__(self):
        self.datamart_name = "datamart"

    def load(self):
        # Full refresh approach for the distribution table
        delete_query = f"TRUNCATE TABLE {self.datamart_name}.fact_class_engagement_distribution;"
        db.execute_query(delete_query)
        
        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_class_engagement_distribution (
                course_key, week_of_year, year, avg_engagement_score, 
                p25_engagement, p50_engagement, p75_engagement, 
                medium_engagement_count, low_engagement_count, 
                active_student_count, passive_student_count
            )
            SELECT 
                course_key,
                week_of_year,
                year,
                AVG(engagement_score) as avg_engagement_score,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY engagement_score) as p25_engagement,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY engagement_score) as p50_engagement,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY engagement_score) as p75_engagement,
                COUNT(CASE WHEN engagement_score >= 40 AND engagement_score < 70 THEN 1 END) as medium_engagement_count,
                COUNT(CASE WHEN engagement_score > 0 AND engagement_score < 40 THEN 1 END) as low_engagement_count,
                COUNT(CASE WHEN engagement_score >= 70 THEN 1 END) as active_student_count,
                COUNT(CASE WHEN engagement_score = 0 THEN 1 END) as passive_student_count
            FROM {self.datamart_name}.fact_risk_student_weekly
            GROUP BY course_key, week_of_year, year;
        """
        db.execute_query(insert_query)