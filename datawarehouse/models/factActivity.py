from utils.pgsql_utils import db

class FactActivity:

    def __init__(self):
        self.db = db
        self.table_name = "fact_activity"
        self.create_table()

    def create_table(self):
        schema_name = self.db.get_schema_name()
        schema = f"""
            activity_id VARCHAR(255) ,
            actor_id VARCHAR(255) ,
            time_id VARCHAR(255) ,
            activity_type VARCHAR(255),
            activity_order INT,
            is_mandatory BOOLEAN ,
            context_id VARCHAR(255) ,
            session_id VARCHAR(255) ,
            CONSTRAINT PK_fact_activity PRIMARY KEY (activity_id, actor_id, time_id),
            CONSTRAINT FK_fact_activity_actor FOREIGN KEY (actor_id) REFERENCES {schema_name}.dim_actor(actor_id), 
            CONSTRAINT FK_fact_activity_context FOREIGN KEY (context_id) REFERENCES {schema_name}.dim_context(context_id),
            CONSTRAINT FK_fact_activity_time FOREIGN KEY (time_id) REFERENCES {schema_name}.dim_time(time_id)
        """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = """ ON CONFLICT (activity_id, actor_id, time_id)
                        DO UPDATE NOTHING;
                    """
        self.db.insert_many_records(self.table_name, objects, condition)


