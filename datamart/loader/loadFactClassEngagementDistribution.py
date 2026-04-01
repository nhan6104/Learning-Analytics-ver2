"""
Load Fact Class Engagement Distribution V2

This V2 loader updates thresholds to match V2 engagement scoring.

Fixes Bug 5: Engagement Distribution Thresholds
- Uses V2 thresholds (Excellent 80-100, Good 60-79, Warning 40-59, Critical <40)
- Adds new category columns for V2
- Maintains backward compatibility with V1 columns
"""

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
                course_key, week_of_year, year, 
                avg_engagement_score, 
                p25_engagement, p50_engagement, p75_engagement,
                -- V2 categories (new thresholds)
                excellent_student_count, good_student_count, 
                warning_student_count, critical_student_count,
                -- V1 categories (backward compatibility)
                active_student_count, medium_engagement_count, 
                low_engagement_count, passive_student_count
            )
            SELECT 
                course_key,
                week_of_year,
                year,
                ROUND(AVG(engagement_score)::NUMERIC, 2) as avg_engagement_score,
                ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY engagement_score)::NUMERIC, 2) as p25_engagement,
                ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY engagement_score)::NUMERIC, 2) as p50_engagement,
                ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY engagement_score)::NUMERIC, 2) as p75_engagement,
                
                -- V2 Thresholds (based on new scoring: Resource 40% + Quiz 40% + Time 20%)
                COUNT(CASE WHEN engagement_score >= 80 THEN 1 END) as excellent_student_count,
                COUNT(CASE WHEN engagement_score >= 60 AND engagement_score < 80 THEN 1 END) as good_student_count,
                COUNT(CASE WHEN engagement_score >= 40 AND engagement_score < 60 THEN 1 END) as warning_student_count,
                COUNT(CASE WHEN engagement_score > 0 AND engagement_score < 40 THEN 1 END) as critical_student_count,
                
                -- V1 Thresholds (backward compatibility)
                COUNT(CASE WHEN engagement_score >= 70 THEN 1 END) as active_student_count,
                COUNT(CASE WHEN engagement_score >= 40 AND engagement_score < 70 THEN 1 END) as medium_engagement_count,
                COUNT(CASE WHEN engagement_score > 0 AND engagement_score < 40 THEN 1 END) as low_engagement_count,
                COUNT(CASE WHEN engagement_score = 0 THEN 1 END) as passive_student_count
                
            FROM {self.datamart_name}.fact_risk_student_weekly
            GROUP BY course_key, week_of_year, year;
        """
        db.execute_query(insert_query)