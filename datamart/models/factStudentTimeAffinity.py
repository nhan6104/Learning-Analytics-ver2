from utils.pgsql_utils import db

class FactStudentTimeAffinity:
    def __init__(self):
        self.db = db
        self.table_name = "fact_student_time_affinity"
        self.create_table()

    def create_table(self):
        schema = """
            student_key VARCHAR(255),
            course_key VARCHAR(255),
            time_slot VARCHAR(50),
            efficiency_index DECIMAL(5,2),
            total_engagement_score INT,
            session_count INT,
            CONSTRAINT PK_fact_student_time_affinity PRIMARY KEY (student_key, course_key, time_slot)
            """
        self.db.create_table(self.table_name, schema)

    def update_datamart(self, query):
        self.db.execute_query(query)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
