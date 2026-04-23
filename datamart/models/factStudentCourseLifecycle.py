from utils.pgsql_utils import db


class FactStudentCourseLifeCycle:
    def __init__(self):
        self.db = db
        self.table_name = "fact_student_course_lifecycle"
        self.create_table()

    def create_table(self):
        schema = """
            student_key VARCHAR(255),
            course_key INT,
            milestone_25_date DATE,
            milestone_50_date DATE,
            milestone_75_date DATE,
            completion_date DATE,
            current_progress_pct INT,
            completed_module_count INT,
            dropout_date DATE,
            total_module_count INT,
            current_status VARCHAR(255),
            days_since_last_activity INT,
            last_activity_date DATE,
            CONSTRAINT PK_fact_student_course_lifecycle PRIMARY KEY (student_key, course_key)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)

    def update_datamart(self, query):
        self.db.execute_query(query)