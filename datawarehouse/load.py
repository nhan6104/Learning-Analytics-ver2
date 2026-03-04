from datawarehouse.models.dimActor import DimActor
from datawarehouse.models.dimContext import DimContext
from datawarehouse.models.dimInteractionType import DimInteractionType
from datawarehouse.models.dimTime import DimTime
from datawarehouse.models.factActivity import FactActivity
from datawarehouse.models.factQuestion import FactQuestion
from datawarehouse.models.factQuiz import FactQuiz
from datawarehouse.models.factSession import FactSession
from datawarehouse.models.factStatement import FactStatement
from utils.pgsql_utils import db



class DataLoader:
    def __init__(self):
        self.db = db
        schema_name = "datawarehouse"
        self.db.create_schema(schema_name)
        self.dimInteractionTypeModel = DimInteractionType()
        self.dimContextModel = DimContext()
        self.dimTimeModel = DimTime()
        self.dimActorModel = DimActor()
        self.factQuizModel = FactQuiz()
        self.factStatementModel = FactStatement()
        self.factQuestionModel = FactQuestion()
        self.factSessionModel = FactSession()
        self.factActivityModel = FactActivity()  

    def insert_data(self, table_name, data):
        if table_name == "fact_statement":
            self.factStatementModel.insert_many_records(data)
        elif table_name == "fact_session":  
            self.factSessionModel.insert_many_records(data)
        elif table_name == "fact_activity": 
            self.factActivityModel.insert_many_records(data)
        elif table_name == "fact_quiz": 
            self.factQuizModel.insert_many_records(data)
        elif table_name == "dim_interaction_type":
            self.dimInteractionTypeModel.insert_many_records(data)
        elif table_name == "dim_context":
            self.dimContextModel.insert_many_records(data)
        elif table_name == "dim_time":
            self.dimTimeModel.insert_many_records(data)
        elif table_name == "fact_question":
            self.factQuestionModel.insert_many_records(data)
        elif table_name == "dim_actor":
            self.dimActorModel.insert_many_records(data)


    def load_data(self, statements):
        for table_name, data in statements.items():
            if data and len(data) > 0:
                self.insert_data(table_name, data)

    