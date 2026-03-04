from utils.pgsql_utils import db

class FactStatement:

    def __init__(self):
        self.db = db
        self.table_name = "fact_statement"
        self.create_table()

    def create_table(self):
        schema_name = self.db.schema
        schema = f"""
            event_id VARCHAR(255),
            actor_id VARCHAR(255),
            interaction_id VARCHAR(255),
            context_id VARCHAR(255),
            object_id VARCHAR(255),
            object_type VARCHAR(255) ,
            time_id VARCHAR(255) ,
            timestamp TIMESTAMP ,
            CONSTRAINT PK_fact_statement PRIMARY KEY (event_id),
            CONSTRAINT FK_fact_statement_actor FOREIGN KEY (actor_id) REFERENCES {schema_name}.dim_actor(actor_id),
            CONSTRAINT FK_fact_statement_interaction FOREIGN KEY (interaction_id) REFERENCES {schema_name}.dim_interaction_type(interaction_id),
            CONSTRAINT FK_fact_statement_context FOREIGN KEY (context_id) REFERENCES {schema_name}.dim_context(context_id),
            CONSTRAINT FK_fact_statement_time FOREIGN KEY (time_id) REFERENCES {schema_name}.dim_time(time_id)
        """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = "ON CONFLICT (event_id) DO NOTHING;"
        self.db.insert_many_records(self.table_name, objects, condition)