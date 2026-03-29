from utils.pgsql_utils import db

class DimSection:
    def __init__(self):
        self.db = db
        self.table_name = "dim_section"
        self.create_table()

    def create_table(self):
        schema = """
            section_key VARCHAR(255) PRIMARY KEY,
            section_name VARCHAR(255),
            section_number INT,
            course_key VARCHAR(255)
            """
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)
