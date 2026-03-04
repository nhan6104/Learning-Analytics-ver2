# from datawarehouse.models.dimActor import DimActor
# from datawarehouse.models.dimContext import DimContext
# from datawarehouse.models.dimInteractionType import DimInteractionType
# from datawarehouse.models.dimTime import DimTime
# from datawarehouse.models.factActivity import FactActivity
# from datawarehouse.models.factQuestion import FactQuestion
# from datawarehouse.models.factQuiz import FactQuiz
# from datawarehouse.models.factSession import FactSession
# from datawarehouse.models.factStatement import FactStatement
from utils.pgsql_utils import db

schema_name = "datawarehouse"
db.create_schema(schema_name)



# dimInteractionTypeModel = DimInteractionType()
# dimContextModel = DimContext()
# dimTimeModel = DimTime()
# dimActorModel = DimActor()
# factSessionModel = FactSession()
# factActivityModel = FactActivity()  
# factQuizModel = FactQuiz()
# factQuestionModel = FactQuestion()
# factStatementModel = FactStatement()
