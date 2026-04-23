from utils.pgsql_utils import db

class FactQuiz:

    def __init__(self):
        self.db = db
        self.table_name = "fact_quiz"
        self.create_table()

    def create_table(self):
        schema_name = self.db.get_schema_name()
        schema = f"""
            quiz_attempt_id VARCHAR(255) ,
            quiz_id INT,
            attempt_no INT,
            actor_id VARCHAR(255) ,
            start_time TIMESTAMP ,
            end_time TIMESTAMP ,
            score INT ,
            completion_status BOOLEAN ,
            isSucceed BOOLEAN ,
            time_id VARCHAR(255) ,
            duration BIGINT ,
            context_id VARCHAR(255) ,
            CONSTRAINT PK_fact_quiz PRIMARY KEY (quiz_attempt_id),
            CONSTRAINT FK_fact_quiz_actor FOREIGN KEY (actor_id) REFERENCES {schema_name}.dim_actor(actor_id),
            CONSTRAINT FK_fact_quiz_time FOREIGN KEY (time_id) REFERENCES {schema_name}.dim_time(time_id),
            CONSTRAINT FK_fact_quiz_context FOREIGN KEY (context_id) REFERENCES {schema_name}.dim_context(context_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, conn, objects):
        condition = """ ON CONFLICT (quiz_attempt_id)
                        DO UPDATE SET
                            score = COALESCE(EXCLUDED.score, fact_quiz.score),
                            quiz_id = EXCLUDED.quiz_id,
                            completion_status = COALESCE(EXCLUDED.completion_status, fact_quiz.completion_status),
                            isSucceed = COALESCE(EXCLUDED.isSucceed, fact_quiz.isSucceed),
                            duration = COALESCE(EXCLUDED.duration, fact_quiz.duration),
                            attempt_no = EXCLUDED.attempt_no,
                            end_time = CASE
                                WHEN EXCLUDED.completion_status = TRUE THEN EXCLUDED.end_time
                                ELSE fact_quiz.end_time
                            END;
                    """
        self.db.insert_many_records(conn, self.table_name, objects, condition)