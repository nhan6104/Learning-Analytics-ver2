from utils.pgsql_utils import db


class FactBehaviorOutcomeCorrelation:
    def __init__(self):
        self.db = db
        self.table_name = "fact_behavior_outcome_correlation"
        self.create_table()

    def create_table(self):
        schema = """
            course_key VARCHAR(255),
            week_of_year INT,
            year INT,
            correlation_active_learning_score INT,
            correlation_cram_failure INT,
            avg_final_score DECIMAL(5,2),
            cram_student_count INT            
            """
        
        self.db.create_table(self.table_name, schema)

    def update_datamart(self, query):
        self.db.execute_query(query)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)