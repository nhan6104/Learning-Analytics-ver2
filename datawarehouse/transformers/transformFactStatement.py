from utils.dataExtractorUtils import DataExtractor

class transformFactStatement:
    def __init__(self):
        pass

    def transform(self, statement, kwargs = {}):
        event_id = statement.id
        actor_id = statement.actor.account.name if statement.actor.account else None
        full_verb_id = statement.verb.id
        interaction_id = full_verb_id.strip('/').split('/')[-1]
        
        timestamp = DataExtractor.parse_timestamp(statement.timestamp)

        

        # object_type = statement.object.objectType
        xAPI_object_id = statement.object.id
        xAPI_object_id_el = xAPI_object_id.split('/')

        object_category = "system"
        object_id = "moodle"
        print(xAPI_object_id)
        if "resource" in xAPI_object_id_el:
            object_id = "resource_" + xAPI_object_id.split('=')[-1]
            object_category = "resource"
        elif "course" in xAPI_object_id_el:
            object_id = "course_" + xAPI_object_id.split('=')[-1]
            object_category = "course"
        elif "forum" in xAPI_object_id_el:
            object_id = "forum_" + xAPI_object_id.split('=')[-1]
            object_category = "forum"


        time_id = kwargs.get("time_id", "")
        context_id = kwargs.get("context_id", "")

        return {
            "event_id":       event_id,
            "actor_id":       actor_id,
            "interaction_id": interaction_id,
            "timestamp":      timestamp,
            "context_id":     context_id,
            "object_id":      object_id,
            "object_type":    object_category,
            "time_id":        time_id,
        }