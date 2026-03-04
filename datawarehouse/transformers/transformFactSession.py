from utils.dataExtractorUtils import DataExtractor

class transformFactSession:
    def __init__(self):
        pass    


    def transform(self, statement, kwargs = {}):
        # startTime = lấy thời gian kết thúc của sự kiện trước đó
        # endTime =  data.get("timestamp ", {})
        # timeId
        if not statement.context or not statement.context.registration:
            return {}

        session_id = statement.context.registration
        actor_id = statement.actor.account.name if statement.actor.account else None
        timestamp = DataExtractor.parse_timestamp(statement.timestamp)

        # 1. Simplify Entry Point (e.g., extracting 'quiz', 'course', 'page')
        full_object_id = statement.object.id if statement.object else ""
        entry_point = "other"
        if 'quiz' in full_object_id.lower():
            entry_point = "quiz"
        elif 'course' in full_object_id.lower():
            entry_point = "course"
        elif 'page' in full_object_id.lower():
            entry_point = "page"
        elif 'resource' in full_object_id.lower():
            entry_point = "resource"
            
        # 2. Context ID is passed from outside
        
        # 3. Default session type
        session_type = "learning"

        timeId = kwargs.get("time_id", "")
        context_id = kwargs.get("context_id", "")

        return {
            "session_id": session_id,
            "actor_id": actor_id,
            "entry_point": entry_point,
            "end_time": timestamp,
            "time_id": timeId,
            "start_time": timestamp,
            "end_time": timestamp,
            "context_id": context_id,
            "session_type": session_type
        }
        