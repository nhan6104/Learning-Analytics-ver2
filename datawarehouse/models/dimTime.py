from utils.pgsql_utils import db

class DimTime:

    def __init__(self):
        self.db = db
        self.table_name = "dim_time"
        self.create_table()

    def create_table(self):
        schema = """
            time_id VARCHAR(255) ,
            date INT ,
            month INT ,
            year INT ,
            week INT ,
            day_of_week VARCHAR(255) ,
            time_slot VARCHAR(255) ,
            CONSTRAINT PK_dim_time PRIMARY KEY (time_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = """ON CONFLICT (time_id) DO NOTHING"""
        self.db.insert_many_records(self.table_name, objects, condition)