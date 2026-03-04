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
            isComplete BOOLEAN ,
            isSucceed BOOLEAN ,
            time_id VARCHAR(255) ,
            duration BIGINT ,
            CONSTRAINT PK_fact_quiz PRIMARY KEY (quiz_attempt_id),
            CONSTRAINT FK_fact_quiz_actor FOREIGN KEY (actor_id) REFERENCES {schema_name}.dim_actor(actor_id),
            CONSTRAINT FK_fact_quiz_time FOREIGN KEY (time_id) REFERENCES {schema_name}.dim_time(time_id)
            """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = """ ON CONFLICT (quiz_attempt_id)
                        DO UPDATE SET
                            total_score = COALESCE(EXCLUDED.total_score, fact_quiz.total_score),
                            max_score   = COALESCE(EXCLUDED.max_score, fact_quiz.max_score),
                            quiz_id     = COALESCE(EXCLUDED.quiz_id, fact_quiz.quiz_id),
                            isComplete  = COALESCE(EXCLUDED.isComplete, fact_quiz.isComplete),
                            isSucceed   = COALESCE(EXCLUDED.isSucceed, fact_quiz.isSucceed),
                            raw_duration_ms = COALESCE(EXCLUDED.raw_duration_ms, fact_quiz.raw_duration_ms),
                            attempt_no  = COALESCE(EXCLUDED.attempt_no, fact_quiz.attempt_no),
                            end_time = CASE
                                WHEN EXCLUDED.isComplete = 1 THEN EXCLUDED.end_time
                                ELSE fact_quiz.end_time
                            END;
                    """
        self.db.insert_many_records(self.table_name, objects, condition)