import logging
from utils.dataExtractorUtils import DataExtractor
from utils.moodle_db_utils import moodle_db
from urllib.parse import urlparse, parse_qs


logger = logging.getLogger(__name__)

class transformFactActivity:

    def __init__(self):
        self.db = moodle_db

    def parse_activity_id(self, url: str):
        url = url.strip('"')

        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        query = parse_qs(parsed.query)

        module = None
        resource = None
        primary_id = None
        attempt_id = None
        question_id = None
        chapter_id = None

        # ===== 1. Detect module + resource =====
        if "mod" in path_parts:
            idx = path_parts.index("mod")
            module = path_parts[idx + 1]                  # book
            resource = path_parts[-1].split('.')[0]       # view

        elif "course" in path_parts:
            module = "course"
            resource = path_parts[-1].split('.')[0]         # view / section

        elif "question" in path_parts:
            module = "quiz"                                 # normalize
            resource = "question"

        else:
            # fallback (review.php, etc.)
            module = "quiz"
            resource = path_parts[-1].split('.')[0]

        # ===== 2. Extract IDs =====
        if module == "course":
            primary_id = query.get("id", [None])[0]

        elif module == "quiz":
            primary_id = query.get("cmid", query.get("id", [None]))[0]
            attempt_id = query.get("attempt", [None])[0]

            if resource == "question":
                question_id = query.get("id", [None])[0]

        elif module == "book":
            primary_id = query.get("id", [None])[0]
            chapter_id = query.get("chapterid", [None])[0]
        else:
            # forum / resource / assign
            primary_id = query.get("id", [None])[0]

        # ===== 3. Build activity_id =====
        if module == "book" and chapter_id:
            resource = "chapter"

        parts = [module, resource]

        if primary_id:
            parts.append(str(primary_id))

        if attempt_id:
            parts.append(str(attempt_id))

        if question_id:
            parts.append(str(question_id))

        if chapter_id:
            parts.append(str(chapter_id))

        activity_id = "_".join(parts)

        return activity_id

    def transform(self, statement, kwargs = {}):
        
        res = []
        if not statement.context or not statement.context.registration:
            return res
        
        session_id =  statement.context.registration
        context_id = kwargs.get("context_id", "")
        time_id = kwargs.get("time_id", "")

        if not statement.object.id:
            return res
        

        # activityId = statement.object.id.split('/')       
        # activity = activityId[-2]
        # resource = activityId[-1].split('.')[0]
        # print(activityId)
        # idResource = activityId[-1].split('=')[1]

        activity_id = self.parse_activity_id(statement.object.id)


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
                parent_activity_id = self.parse_activity_id(el.id)

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