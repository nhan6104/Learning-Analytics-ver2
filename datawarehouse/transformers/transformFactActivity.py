import logging
from utils.dataExtractorUtils import DataExtractor
from utils.moodle_db_utils import moodle_db


logger = logging.getLogger(__name__)

class transformFactActivity:

    def __init__(self):
        self.db = moodle_db
        

    def transform(self, statement, kwargs = {}):
        
        res = []
        if not statement.context or not statement.context.registration:
            return res
        
        session_id =  statement.context.registration
        context_id = kwargs.get("context_id", "")
        time_id = kwargs.get("time_id", "")

        if not statement.object.id:
            return res
        

        activityId = statement.object.id.split('/')
        if len(activityId) < 2:
             return res

        activity = activityId[-2]
        last_part = activityId[-1]
        
        resource = last_part.split('.')[0]
        
        if '=' in last_part:
            idResource = last_part.split('=')[1]
        else:
            idResource = last_part

        activity_id = activity + '_' + resource + '_' + idResource


        actor_id = None
        if statement.actor and statement.actor.account:
            actor_id = statement.actor.account.name

        activity_type = ""
        if statement.object and statement.object.definition:
            activity_type = statement.object.definition.type.split("/")[-1]

        activity_category = None
        if activity_type in ["resource", "course"]:
            activity_category = "learning"

        elif activity_type in ["forum"]:
            activity_category = "discuss"
    
        elif activity_type in ["attempt"]:
            activity_category = "assesment"
        
        parentCount = 0
        if statement.context.contextActivities and statement.context.contextActivities.parent:
            parentCount = len(statement.context.contextActivities.parent)

        activity_order = 1
        activityEl = {
            "activity_id": activity_id,
            "activity_type": activity_category,
            "activity_order": activity_order,
            "context_id": context_id,
            "actor_id": actor_id,
            "time_id": time_id,
            "session_id": session_id
        }

        if parentCount == 0:
            res.append(activityEl)
            return res
        
        else:
            activityEl["activity_order"] = parentCount + 1
            res.append(activityEl)
            offset = 0
            for el in  statement.context.contextActivities.parent:
                parentId = el.id.split('/')
                if len(parentId) < 2:
                    offset += 1
                    continue
                                    
                parentActivity = parentId[-2]
                parentLastPart = parentId[-1]
                parentResource = parentLastPart.split('.')[0]
                
                if '=' in parentLastPart:
                    parentIdResource = parentLastPart.split('=')[1]
                else:
                    parentIdResource = parentLastPart
                parent_activity_id = parentActivity + '_' + parentResource + '_' + parentIdResource

                parent_activity_type = ""
                if el.definition:
                    parent_activity_type = el.definition.type.split("/")[-1]

                parent_activity_category = None
                if parent_activity_type in ["resource", "course"]:
                    parent_activity_category = "learning"

                elif parent_activity_type in ["forum"]:
                    parent_activity_category = "discuss"
            
                elif parent_activity_type in ["attempt"]:
                    parent_activity_category = "assesment"

                parent_activity_order = parentCount - offset
                offset += 1

                res.append({
                    "activity_id": parent_activity_id,
                    "activity_type": parent_activity_category,
                    "activity_order": parent_activity_order,
                    "context_id": context_id,
                    "actor_id": actor_id,
                    "time_id": time_id,
                    "session_id": session_id
                })  

        return res
    
        # # 1. Logic for completion_status
        # completion_status = "In Progress"
        # if statement.result and statement.result.completion is True:
        #     completion_status = "Completed"
        # if statement.result and statement.result.success is True:
        #     completion_status = "Passed"
        # elif statement.result and statement.result.success is False:
        #     completion_status = "Failed"

        # # 3. Fetch Moodle Metadata (activity_length, activity_order, is_mandatory)
        # activity_order = None
        # is_mandatory = True  # Default to True
        
        # cmid = DataExtractor.extract_moodle_module_id(activity_id)
        # if cmid:
        #     try:
        #         get_module_info_query = """   
        #                 SELECT cm.section, cm.completion, cm.added
        #                 FROM mdl_course_modules cm
        #                 WHERE cm.id = %s
        #             """
        #         params = (cmid,)
        #         res = self.db.inquiry_query(get_module_info_query, params)
        #         if res:
        #             activity_order = res[0]['section']
        #             is_mandatory = True if res[0]['completion'] > 0 else False
              
            
        #     except Exception as e:
        #         logger.error(f"Error fetching activity metadata from Moodle: {e}")




        # return {
        #     "activity_id": activity_id,
        #     "activity_type": activity_type,
        #     "activity_order": activity_order,
        #     "context_id": context_id,
        #     "actor_id": actor_id,
        #     "is_mandatory": is_mandatory,
        #     "time_id": time_id,
        #     "session_id": session_id
        # }