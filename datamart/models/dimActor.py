from utils.pgsql_utils import db

class DimActor:
    
    def __init__(self):
        self.db = db
        self.table_name = "dim_actor"
        self.create_table()

    def create_table(self):
        schema = """
            actor_id VARCHAR(255) PRIMARY KEY,
            actor_name VARCHAR(255),
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        self.db.insert_many_records(self.table_name, objects)

    def update_datamart(self, query):
        self.db.execute_query(query)