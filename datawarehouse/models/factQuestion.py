from utils.pgsql_utils import db

class FactQuestion:

    def __init__(self):
        self.db = db
        self.table_name = "fact_question"
        self.create_table()

    def create_table(self):
        schema_name = self.db.get_schema_name()
        schema = f"""
            question_id VARCHAR(255) ,
            quiz_attempt_id VARCHAR(255) ,
            selected_answer INT ,
            is_correct INT ,
            quiz_id VARCHAR(255) ,
            start_time TIMESTAMP ,
            attempt_no INT,
            CONSTRAINT PK_fact_question PRIMARY KEY (question_id, quiz_attempt_id),
            CONSTRAINT FK_fact_question_quiz FOREIGN KEY (quiz_attempt_id) REFERENCES {schema_name}.fact_quiz(quiz_attempt_id)
        """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, objects):
        condition = """ ON CONFLICT (question_id, quiz_attempt_id)
                        DO UPDATE SET
                            score = COALESCE(EXCLUDED.score, fact_question.score),
                            max_score = COALESCE(EXCLUDED.max_score, fact_question.max_score),
                            is_correct = COALESCE(EXCLUDED.is_correct, fact_question.is_correct),
                            duration_ms = COALESCE(EXCLUDED.duration_ms, fact_question.duration_ms)
                    """
        self.db.insert_many_records(self.table_name, objects, condition) 