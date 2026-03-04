import logging
from datawarehouse.models.xAPI_model import Statement
from datawarehouse.transformers.transformDimActor import transformDimActor
from datawarehouse.transformers.transformDimContext import transformDimContext
from datawarehouse.transformers.transformDimInteractionType import transformDimInteractionType
from datawarehouse.transformers.transformFactActivity import transformFactActivity
from datawarehouse.transformers.transformFactQuiz import transformFactQuiz
from datawarehouse.transformers.transformFactQuestion import transformFactQuestion
from datawarehouse.transformers.transformFactSession import transformFactSession
from datawarehouse.transformers.transformFactStatement import transformFactStatement
from datawarehouse.transformers.transformDimTime import transformDimTime

logger = logging.getLogger(__name__)

class DataTransformer:
    def __init__(self):
        self.dim_actor_transformer = transformDimActor()
        self.dim_context_transformer = transformDimContext()
        self.dim_interaction_type_transformer = transformDimInteractionType()
        self.fact_statement_transformer = transformFactStatement()
        self.fact_session_transformer = transformFactSession()
        self.fact_quiz_transformer = transformFactQuiz()
        self.fact_question_transformer = transformFactQuestion()
        self.fact_activity_transformer = transformFactActivity()
        self.dim_time_transformer = transformDimTime()


    def transform(self, raw_statements):
        logger.info("Starting data transformation process")
        transformed_statements = {
            "dim_interaction_type": [],
            "dim_time": [],
            "bridge_hierarchy_activity": [],
            "dim_actor": [],
            "dim_activity": [],
            "dim_context": [],
            "fact_activity": [],
            "fact_statement": [],
            "fact_session": [],
            "fact_quiz": [],
            "fact_question": []
        }
        for raw_statement in raw_statements:
            statement = Statement(**raw_statement)
            logger.debug(f"Transforming statement with ID: {statement.id}")

            dim_context = self.dim_context_transformer.transform(statement)
            dim_time = self.dim_time_transformer.transform(statement)

            contextId = dim_context.get("context_id", "")
   

            kwargs = {
                "time_id": dim_time.get("time_id", ""),
                "context_id": contextId
            }

            dim_interaction = self.dim_interaction_type_transformer.transform(statement, kwargs)
            interactionId = dim_interaction.get("interaction_id", "")
            if contextId == "" or contextId == "CTX_0_0_0" or interactionId in ["toured", "enrolled"]:
                continue

            dim_actor = self.dim_actor_transformer.transform(statement, kwargs)
            fact_activity = self.fact_activity_transformer.transform(statement, kwargs)
            fact_statement = self.fact_statement_transformer.transform(statement, kwargs)
            fact_session = self.fact_session_transformer.transform(statement, kwargs)
            fact_quiz = self.fact_quiz_transformer.transform(statement, kwargs)
            fact_question = self.fact_question_transformer.transform(statement, kwargs)

            
            transformed_statements["dim_context"].append(dim_context)
            transformed_statements["dim_time"].append(dim_time)
            transformed_statements["dim_actor"].append(dim_actor)
            transformed_statements["dim_interaction_type"].append(dim_interaction)
            transformed_statements["fact_activity"].extend(fact_activity)
            transformed_statements["fact_statement"].append(fact_statement)
            if fact_session:
                transformed_statements["fact_session"].append(fact_session)
            if fact_quiz:
                transformed_statements["fact_quiz"].append(fact_quiz)
            if fact_question:
                transformed_statements["fact_question"].append(fact_question)

        logger.info("Data transformation process completed")
        return transformed_statements
    
