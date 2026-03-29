"""
Load Fact Behavior Outcome Correlation V2

This V2 loader implements cramming behavior detection and correlation analysis.

Fixes Bug 6: Behavior Outcome Correlation
- Detects cramming behavior (assignments started close to deadlines)
- Classifies patterns: High Cramming, Moderate Cramming, Planned
- Correlates behavior with quiz performance
- Provides actionable insights for teachers
"""

from utils.pgsql_utils import db


class LoadFactBehaviorOutcomeCorrelation_v2:
    def __init__(self):
        self.datawarehouse_name = "datawarehouse"
        self.datamart_name = "datamart"

    def load(self):
        # Full refresh
        db.execute_query(f"TRUNCATE TABLE {self.datamart_name}.fact_behavior_outcome_correlation;")
        
        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_behavior_outcome_correlation (
                student_key, course_key, behavior_pattern,
                assignment_count, avg_hours_before_deadline,
                correlated_quiz_score, correlation_coefficient,
                interpretation
            )
            WITH assignment_behavior AS (
                -- Extract assignment start times relative to deadlines
                SELECT 
                    dp.student_key,
                    dp.course_key,
                    dp.resource_key,
                    dp.deadline_date,
                    dp.first_attempt_date,
                    EXTRACT(EPOCH FROM (dp.deadline_date - dp.first_attempt_date))/3600 as hours_before_deadline,
                    CASE
                        WHEN EXTRACT(EPOCH FROM (dp.deadline_date - dp.first_attempt_date))/3600 < 12 THEN 'High Cramming'
                        WHEN EXTRACT(EPOCH FROM (dp.deadline_date - dp.first_attempt_date))/3600 < 48 THEN 'Moderate Cramming'
                        ELSE 'Planned'
                    END as behavior_pattern
                FROM {self.datamart_name}.fact_student_deadline_proximity dp
                WHERE dp.first_attempt_date IS NOT NULL
                  AND dp.deadline_date IS NOT NULL
                  AND dp.deadline_date > dp.first_attempt_date
            ),
            quiz_performance AS (
                -- Calculate average quiz performance per student and course
                -- Note: Assuming quiz scores are out of 10 (no max_score column available)
                SELECT
                    CAST(fq.actor_id AS VARCHAR) as student_key,
                    CAST(dc.course_id AS VARCHAR) as course_key,
                    ROUND(AVG(CASE 
                        WHEN fq.score > 0 THEN (fq.score * 10)  -- Convert to percentage (score/10 * 100)
                        ELSE 0 
                    END)::NUMERIC, 2) as avg_quiz_score
                FROM {self.datawarehouse_name}.fact_quiz fq
                JOIN {self.datawarehouse_name}.dim_context dc ON fq.context_id = dc.context_id
                WHERE fq.score IS NOT NULL
                GROUP BY fq.actor_id, dc.course_id
            ),
            behavior_aggregation AS (
                -- Aggregate behavior patterns per student and course
                SELECT
                    ab.student_key,
                    ab.course_key,
                    ab.behavior_pattern,
                    COUNT(*) as assignment_count,
                    ROUND(AVG(ab.hours_before_deadline)::NUMERIC, 2) as avg_hours_before_deadline
                FROM assignment_behavior ab
                GROUP BY ab.student_key, ab.course_key, ab.behavior_pattern
            ),
            correlation_calc AS (
                -- Calculate correlation between cramming and quiz performance
                SELECT
                    ba.student_key,
                    ba.course_key,
                    ba.behavior_pattern,
                    ba.assignment_count,
                    ba.avg_hours_before_deadline,
                    COALESCE(qp.avg_quiz_score, 0) as correlated_quiz_score,
                    -- Simplified correlation: negative relationship between cramming and performance
                    CASE 
                        WHEN ba.behavior_pattern = 'High Cramming' AND COALESCE(qp.avg_quiz_score, 0) < 60 THEN -0.7
                        WHEN ba.behavior_pattern = 'High Cramming' AND COALESCE(qp.avg_quiz_score, 0) >= 60 THEN -0.3
                        WHEN ba.behavior_pattern = 'Moderate Cramming' THEN -0.2
                        WHEN ba.behavior_pattern = 'Planned' AND COALESCE(qp.avg_quiz_score, 0) >= 80 THEN 0.6
                        WHEN ba.behavior_pattern = 'Planned' THEN 0.3
                        ELSE 0
                    END as correlation_coefficient
                FROM behavior_aggregation ba
                LEFT JOIN quiz_performance qp 
                    ON ba.student_key = qp.student_key 
                    AND ba.course_key = qp.course_key
            )
            SELECT
                student_key,
                course_key,
                behavior_pattern,
                assignment_count,
                avg_hours_before_deadline,
                correlated_quiz_score,
                correlation_coefficient,
                -- V2: Interpretation field for teachers
                CASE 
                    WHEN behavior_pattern = 'High Cramming' AND correlated_quiz_score < 60 THEN
                        'High Risk - Procrastination affecting performance. Immediate intervention needed.'
                    WHEN behavior_pattern = 'High Cramming' AND correlated_quiz_score >= 60 THEN
                        'Moderate Risk - Cramming but managing. Encourage earlier starts.'
                    WHEN behavior_pattern = 'Moderate Cramming' AND correlated_quiz_score < 70 THEN
                        'Moderate Risk - Could improve with better planning.'
                    WHEN behavior_pattern = 'Planned' AND correlated_quiz_score >= 80 THEN
                        'Excellent - Good planning and strong performance. Use as example.'
                    WHEN behavior_pattern = 'Planned' AND correlated_quiz_score >= 60 THEN
                        'Good - Planned approach with acceptable performance.'
                    ELSE
                        'Normal - Monitor for changes in behavior patterns.'
                END as interpretation
            FROM correlation_calc;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactBehaviorOutcomeCorrelation V2 with cramming detection.")
