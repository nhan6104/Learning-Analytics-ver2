from utils.pgsql_utils import db

class DimCourse:
    
    def __init__(self):
        self.db = db
        self.table_name = "dim_course"
        self.create_table()

    def create_table(self):
        schema = """
            course_key VARCHAR(255) ,
            course_name VARCHAR(255),
            course_level VARCHAR(255),
            total_modules INT,
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
    
    def update_datamart(self, query):
        self.db.execute_query(query)