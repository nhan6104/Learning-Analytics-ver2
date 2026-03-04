from utils.pgsql_utils import db


class FactClassEngagementDistribution:
    def __init__(self):
        self.db = db
        self.table_name = "fact_class_engagement_distribution"
        self.create_table()

    def create_table(self):
        schema = """
            course_key VARCHAR(255),
            week_of_year INT,
            year INT,
            avg_engagement_score DECIMAL(5,2),
            p25_engagement INT,
            p50_engagement INT,
            p75_engagement INT,
            medium_engagement_count INT,
            low_engagement_count INT,
            active_student_count INT,
            passive_student_count INT
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)

    def update_datamart(self, query):
        self.db.execute_query(query)