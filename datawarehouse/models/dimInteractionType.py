from utils.pgsql_utils import db

class DimInteractionType:

    def __init__(self):
        self.db = db
        self.table_name = "dim_interaction_type"
        self.create_table()

    def create_table(self):
        schema = """
            interaction_id VARCHAR(255) ,
            interaction_name VARCHAR(255) ,
            interaction_category VARCHAR(255) ,
            CONSTRAINT PK_dim_interaction_type PRIMARY KEY (interaction_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = """ ON CONFLICT (interaction_id)
                        DO UPDATE SET
                            interaction_name = EXCLUDED.interaction_name,
                            interaction_category = EXCLUDED.interaction_category;
                    """
        self.db.insert_many_records(self.table_name, objects, condition )