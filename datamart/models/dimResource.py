from utils.pgsql_utils import db

class DimResource:
    
    def __init__(self):
        self.db = db
        self.table_name = "dim_resource"
        self.create_table()

    def create_table(self):
        schema = """
            resource_key VARCHAR(255) PRIMARY KEY,
            resource_name VARCHAR(255),
            resource_type VARCHAR(255),
            course_key VARCHAR(255)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
    
    def update_datamart(self, query):
        self.db.execute_query(query)
