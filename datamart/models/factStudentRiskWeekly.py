from utils.pgsql_utils import db


class FactRiskStudentWeekly:
    def __init__(self):
        self.db = db
        self.table_name = "fact_risk_student_weekly"
        self.create_table()

    def create_table(self):
        schema = """
            student_key VARCHAR(255),
            course_key INT,
            week_of_year INT,
            year INT,
            engagement_score INT,
            progress_score INT,
            outcome_score INT,
            engagement_trend DECIMAL(10,2),
            inactivity_days INT,
            progress_lag_pct DECIMAL(10,2),
            social_isolation_score INT,
            risk_score INT,
            dropout_probability_pct DECIMAL(5,2),
            risk_level VARCHAR(255)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)

    def update_datamart(self, query):
        self.db.execute_query(query)