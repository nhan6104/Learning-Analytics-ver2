from utils.pgsql_utils import db

class LoadFactStudentEngagementDepth:
    def __init__(self):
        self.dm = "datamart"
        self.dw = "datawarehouse"

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_engagement_depth;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_student_engagement_depth (
                student_key, course_key, resource_key, 
                depth_ratio, engagement_type
            )
            WITH class_median AS (
                -- Calculate median interaction count per resource as "expected interactions"
                SELECT 
                    context_id,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interaction_count) as median_interactions
                FROM (
                    SELECT context_id, actor_id, COUNT(*) as interaction_count
                    FROM {self.dw}.fact_activity
                    GROUP BY context_id, actor_id
                ) t
                GROUP BY context_id
            )
            SELECT 
                a.actor_id as student_key,
                CAST(c.course_id AS VARCHAR) as course_key,
                CAST(c.resource_id AS VARCHAR) as resource_key,
                ROUND(CAST(CAST(COUNT(a.activity_id) AS NUMERIC) / GREATEST(m.median_interactions, 1) AS NUMERIC), 2) as depth_ratio,
                CASE 
                    WHEN (COUNT(a.activity_id) / GREATEST(m.median_interactions, 1)) < 0.5 THEN 'Skimming'
                    WHEN (COUNT(a.activity_id) / GREATEST(m.median_interactions, 1)) > 1.5 THEN 'Stuck'
                    ELSE 'Deep Dive'
                END as engagement_type
            FROM {self.dw}.fact_activity a
            JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
            JOIN class_median m ON a.context_id = m.context_id
            WHERE c.resource_id IS NOT NULL
            GROUP BY a.actor_id, c.course_id, c.resource_id, m.median_interactions;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactStudentEngagementDepth.")
