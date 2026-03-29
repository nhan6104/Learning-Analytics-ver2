from utils.pgsql_utils import db

class FactStudentDeadlineProximity:
    def __init__(self):
        self.db = db
        self.table_name = "fact_student_deadline_proximity"
        self.create_table()

    def create_table(self):
        schema = """
            student_key VARCHAR(255),
            course_key VARCHAR(255),
            resource_key VARCHAR(255),
            deadline_date TIMESTAMP,
            first_attempt_date TIMESTAMP,
            pressure_level VARCHAR(50),
            CONSTRAINT PK_fact_student_deadline_proximity PRIMARY KEY (student_key, course_key, resource_key)
            """
        self.db.create_table(self.table_name, schema)

    def update_datamart(self, query):
        self.db.execute_query(query)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
