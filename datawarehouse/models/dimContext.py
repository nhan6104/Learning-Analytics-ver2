from utils.pgsql_utils import db

class DimContext:

    def __init__(self):
        self.db = db
        self.table_name = "dim_context"
        self.create_table()

    def create_table(self):
        schema = """
            context_id VARCHAR(255) ,
            section_id VARCHAR(255) ,
            course_id VARCHAR(255) ,
            resource_id VARCHAR(255) ,
            learning_path_id VARCHAR(255) ,
            CONSTRAINT PK_dim_context PRIMARY KEY (context_id)
            """
        
        self.db.create_table(self.table_name, schema)
        
    def insert_many_records(self, conn, objects):
        condition = """ ON CONFLICT (context_id)
                        DO UPDATE SET
                            course_id = EXCLUDED.course_id,
                            section_id = EXCLUDED.section_id,
                            learning_path_id = EXCLUDED.learning_path_id,
                            resource_id = EXCLUDED.resource_id;
                    """
        self.db.insert_many_records(conn, self.table_name, objects, condition)
    