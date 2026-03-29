from utils.pgsql_utils import db

class FactActivityTransitions:
    def __init__(self):
        self.db = db
        self.table_name = "fact_activity_transitions"
        self.create_table()

    def create_table(self):
        schema = """
            course_key VARCHAR(255),
            from_resource_key VARCHAR(255),
            to_resource_key VARCHAR(255),
            transition_count INT,
            CONSTRAINT PK_fact_activity_transitions PRIMARY KEY (course_key, from_resource_key, to_resource_key)
            """
        self.db.create_table(self.table_name, schema)

    def update_datamart(self, query):
        self.db.execute_query(query)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
