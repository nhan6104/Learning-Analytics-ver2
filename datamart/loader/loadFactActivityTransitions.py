"""
Load Fact Activity Transitions V2

This V2 loader fixes resource key extraction to match dim_resource format.

Fixes Bug 4: Activity Transitions Resource Extraction
- Uses context_id to join with dim_context instead of regex extraction
- Preserves module type information
- Ensures successful joins with dim_resource
"""

from utils.pgsql_utils import db


class LoadFactActivityTransitions_v2:
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
                -- Get activity sequences within sessions
                SELECT 
                    c.course_id as course_key,
                    a.context_id,
                    a.activity_id,
                    a.session_id,
                    a.time_id,
                    -- Get the previous activity in the same session
                    LAG(a.context_id) OVER (PARTITION BY a.session_id ORDER BY a.time_id) as prev_context_id,
                    LAG(a.activity_id) OVER (PARTITION BY a.session_id ORDER BY a.time_id) as prev_activity_id
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
            ),
            resource_mapping AS (
                -- V2: Use context_id to get proper resource keys from dim_context
                -- This ensures keys match dim_resource format
                SELECT 
                    ast.course_key,
                    COALESCE(
                        dc_prev.resource_id,
                        'resource_' || regexp_replace(ast.prev_activity_id, '[^0-9]', '', 'g')
                    ) as from_resource_key,
                    COALESCE(
                        dc_curr.resource_id,
                        'resource_' || regexp_replace(ast.activity_id, '[^0-9]', '', 'g')
                    ) as to_resource_key
                FROM activity_steps ast
                LEFT JOIN {self.dw}.dim_context dc_prev ON ast.prev_context_id = dc_prev.context_id
                LEFT JOIN {self.dw}.dim_context dc_curr ON ast.context_id = dc_curr.context_id
                WHERE ast.prev_context_id IS NOT NULL
                  AND ast.prev_activity_id <> ast.activity_id  -- Exclude self-transitions
            )
            SELECT 
                course_key,
                from_resource_key,
                to_resource_key,
                COUNT(*) as transition_count
            FROM resource_mapping
            WHERE from_resource_key IS NOT NULL 
              AND to_resource_key IS NOT NULL
              AND from_resource_key <> ''
              AND to_resource_key <> ''
              AND from_resource_key <> to_resource_key  -- Double-check no self-transitions
            GROUP BY course_key, from_resource_key, to_resource_key;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactActivityTransitions V2 with proper resource key matching.")
