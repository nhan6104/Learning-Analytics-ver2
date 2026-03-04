from utils.pgsql_utils import db


class FactDailyStudentEngagement:
    def __init__(self):
        self.db = db
        self.table_name = "fact_daily_student_engagement"
        self.create_table()

    def create_table(self):
        schema = """
            student_key VARCHAR(255),
            course_key INT,
            date_key VARCHAR(255),
            total_active_minutes INT,
            total_resource_access INT,
            total_quiz_attempt INT,
            engagement_score INT,
            active_learning_index INT,
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)

    def update_datamart(self, query):
        self.db.execute_query(query)