from utils.pgsql_utils import db

class FactSession:

    def __init__(self):
        self.db = db
        self.table_name = "fact_session"
        self.schema_name = self.db.get_schema_name()
        self.create_table()

    def create_table(self):
        schema = f"""
            session_id VARCHAR(255) ,
            actor_id VARCHAR(255) ,
            entry_point VARCHAR(255) ,
            session_type VARCHAR(255),
            session_duration INT DEFAULT 0,
            start_time TIMESTAMP ,
            end_time TIMESTAMP,
            context_id VARCHAR(255) ,
            time_id VARCHAR(255) ,
            CONSTRAINT PK_fact_session PRIMARY KEY (session_id),
            CONSTRAINT FK_fact_session_actor FOREIGN KEY (actor_id) REFERENCES {self.schema_name}.dim_actor(actor_id),
            CONSTRAINT FK_fact_session_context FOREIGN KEY (context_id) REFERENCES {self.schema_name}.dim_context(context_id),
            CONSTRAINT FK_fact_session_time FOREIGN KEY (time_id) REFERENCES {self.schema_name}.dim_time(time_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, conn, objects):
        condition = f"""ON CONFLICT (session_id)
                        DO UPDATE SET
                            start_time = EXCLUDED.start_time,
                            end_time = EXCLUDED.end_time,
                            session_duration = EXCLUDED.session_duration,
                            context_id = EXCLUDED.context_id;
                    """
        self.db.insert_many_records(conn, self.table_name, objects, condition)