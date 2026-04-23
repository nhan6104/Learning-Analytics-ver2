from utils.pgsql_utils import db

class LoadFactActivityTransitionsDetail:
    def __init__(self):
        self.dw = "datawarehouse"
        self.dm = "datamart"

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_activity_transitions_detail;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_activity_transitions_detail (
                student_key, course_key, from_resource_key, to_resource_key, transition_count
            )
            WITH student_sequences AS (
                SELECT 
                    a.actor_id AS student_key,
                    c.course_id,
                    c.resource_id AS from_res,
                    LEAD(c.resource_id) OVER (
                        PARTITION BY a.actor_id, c.course_id
                        ORDER BY a.time_id, a.activity_order
                    ) AS to_res
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE c.resource_id IS NOT NULL
            )
            SELECT 
                student_key,
                CAST(course_id AS VARCHAR) as course_key,
                CAST(from_res AS VARCHAR) as from_resource_key,
                CAST(to_res AS VARCHAR) as to_resource_key,
                COUNT(*) as transition_count
            FROM student_sequences
            WHERE to_res IS NOT NULL 
              AND from_res <> to_res
            GROUP BY student_key, course_id, from_res, to_res;
        """
        db.execute_query(insert_query)
