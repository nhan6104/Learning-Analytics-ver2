from utils.pgsql_utils import db

class FactActivityTransitionsDetail:
    def __init__(self):
        self.table_name = "datamart.fact_activity_transitions_detail"

    def create_table(self):
        query = f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                student_key VARCHAR(255),
                course_key VARCHAR(255),
                from_resource_key VARCHAR(255),
                to_resource_key VARCHAR(255),
                transition_count INT DEFAULT 1,
                PRIMARY KEY (student_key, course_key, from_resource_key, to_resource_key)
            );
        """
        db.execute_query(query)
