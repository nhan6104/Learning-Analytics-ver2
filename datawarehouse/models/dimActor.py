from utils.pgsql_utils import db

class DimActor:

    def __init__(self):
        self.db = db
        self.table_name = "dim_actor"
        self.create_table()

    def create_table(self):
        schema = """
            actor_id VARCHAR(255) ,
            actor_name VARCHAR(255),
            CONSTRAINT PK_dim_actor PRIMARY KEY (actor_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, conn, objects):
        condition = "ON CONFLICT (actor_id) DO UPDATE SET actor_name = EXCLUDED.actor_name;"
        self.db.insert_many_records(conn, self.table_name, objects, condition)