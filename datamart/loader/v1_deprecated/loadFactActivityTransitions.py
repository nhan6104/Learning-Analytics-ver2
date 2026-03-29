from utils.pgsql_utils import db

class LoadFactActivityTransitions:
    def __init__(self):
        self.dw = "datawarehouse"
        self.dm = "datamart"

    def load(self):
        # Full refresh for transitions
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_activity_transitions;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_activity_transitions (
                course_key, from_resource_key, to_resource_key, 
                transition_count
            )
            WITH activity_steps AS (
                SELECT 
                    c.course_id as course_key,
                    a.activity_id,
                    a.session_id,
                    a.time_id,
                    -- Get the previous activity in the same session
                    LAG(a.activity_id) OVER (PARTITION BY a.session_id ORDER BY a.time_id) as prev_activity_id
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
            )
            SELECT 
                course_key,
                regexp_replace(prev_activity_id, '[^0-9]', '', 'g') as from_resource_key,
                regexp_replace(activity_id, '[^0-9]', '', 'g') as to_resource_key,
                COUNT(*) as transition_count
            FROM activity_steps
            WHERE prev_activity_id IS NOT NULL
              AND regexp_replace(prev_activity_id, '[^0-9]', '', 'g') <> ''
              AND regexp_replace(activity_id, '[^0-9]', '', 'g') <> ''
              AND prev_activity_id <> activity_id
            GROUP BY course_key, from_resource_key, to_resource_key;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactActivityTransitions.")
