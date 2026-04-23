import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
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



    def process_statement(self, raw_statement):
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
        if contextId == "" or contextId == "CTX_0_0_0" or interactionId in ["toured", "enrolled", "imported", "created", "logged in"]:
            return None

        dim_actor = self.dim_actor_transformer.transform(statement, kwargs)
        fact_activity = self.fact_activity_transformer.transform(statement, kwargs)
        fact_statement = self.fact_statement_transformer.transform(statement, kwargs)
        fact_session = self.fact_session_transformer.transform(statement, kwargs)
        fact_quiz = self.fact_quiz_transformer.transform(statement, kwargs)
        fact_question = self.fact_question_transformer.transform(statement, kwargs)

        return {
            "dim_context": dim_context,
            "dim_time": dim_time,
            "dim_actor": dim_actor,
            "dim_interaction_type": dim_interaction,
            "fact_activity": fact_activity,
            "fact_statement": fact_statement,
            "fact_session": fact_session,
            "fact_quiz": fact_quiz,
            "fact_question": fact_question
        }


    def transform(self, raw_statements):
        logger.info("Starting data transformation process")
        transformed_statements = {
            "dim_interaction_type": [],
            "dim_time": [],
            "dim_actor": [],
            "dim_context": [],
            "fact_activity": [],
            "fact_statement": [],
            "fact_session": [],
            "fact_quiz": [],
            "fact_question": []
        }

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self.process_statement, raw_statements))

        for res in results:
            if not res:
                continue

            transformed_statements["dim_context"].append(res["dim_context"])
            transformed_statements["dim_time"].append(res["dim_time"])
            transformed_statements["dim_actor"].append(res["dim_actor"])
            transformed_statements["dim_interaction_type"].append(res["dim_interaction_type"])
            transformed_statements["fact_activity"].extend(res["fact_activity"])
            transformed_statements["fact_statement"].append(res["fact_statement"])

            if res["fact_session"]:
                transformed_statements["fact_session"].append(res["fact_session"])
            if res["fact_quiz"]:
                transformed_statements["fact_quiz"].append(res["fact_quiz"])
            if res["fact_question"]:
                transformed_statements["fact_question"].append(res["fact_question"])

        # Post-process: calculate session_duration from first to last event per session
        if transformed_statements["fact_session"]:
            session_timestamps = {}
            for s in transformed_statements["fact_session"]:
                sid = s["session_id"]
                ts = s["start_time"]  # currently = event timestamp
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                if sid not in session_timestamps:
                    session_timestamps[sid] = {"min": ts, "max": ts}
                else:
                    if ts < session_timestamps[sid]["min"]:
                        session_timestamps[sid]["min"] = ts
                    if ts > session_timestamps[sid]["max"]:
                        session_timestamps[sid]["max"] = ts

            # Deduplicate fact_session by session_id and fill in start/end/duration
            seen_sessions = {}
            for s in transformed_statements["fact_session"]:
                sid = s["session_id"]
                if sid not in seen_sessions:
                    start = session_timestamps[sid]["min"]
                    end = session_timestamps[sid]["max"]
                    duration = int((end - start).total_seconds())
                    s["start_time"] = start
                    s["end_time"] = end
                    s["session_duration"] = duration
                    seen_sessions[sid] = s
            transformed_statements["fact_session"] = list(seen_sessions.values())

        logger.info("Data transformation process completed")
        return transformed_statements
    
