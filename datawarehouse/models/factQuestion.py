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
            selected_answer TEXT ,
            is_correct BOOLEAN ,
            quiz_id VARCHAR(255) ,
            start_time TIMESTAMP ,
            attempt_no INT,
            CONSTRAINT PK_fact_question PRIMARY KEY (question_id, quiz_attempt_id),
            CONSTRAINT FK_fact_question_quiz FOREIGN KEY (quiz_attempt_id) REFERENCES {schema_name}.fact_quiz(quiz_attempt_id)
        """
        
        self.db.create_table(self.table_name, schema)

    def insert_many_records(self, conn, objects):
        condition = """ ON CONFLICT (question_id, quiz_attempt_id)
                        DO UPDATE SET
                            selected_answer = COALESCE(EXCLUDED.selected_answer, fact_question.selected_answer),
                            is_correct = COALESCE(EXCLUDED.is_correct, fact_question.is_correct),
                            quiz_id = COALESCE(EXCLUDED.quiz_id, fact_question.quiz_id),
                            start_time = COALESCE(EXCLUDED.start_time, fact_question.start_time),
                            attempt_no = COALESCE(EXCLUDED.attempt_no, fact_question.attempt_no)
                    """
        self.db.insert_many_records(conn, self.table_name, objects, condition) 