
import logging
from utils.moodle_db_utils import moodle_db
from utils.dataExtractorUtils import DataExtractor

logger = logging.getLogger(__name__)

class transformDimContext:

    def __init__(self):
        self.db = moodle_db

    def transform(self, statement, kwargs = {}):
        course_id = DataExtractor.extract_moodle_course_id(statement)
        resource_id = DataExtractor.extract_moodle_module_id(statement.object.id if statement.object else "")
    
        section_id = None
        learning_path_id = None
        
        # 1. Try xAPI Extensions
        if statement.context and statement.context.extensions:
            for key, val in statement.context.extensions.items():
                if 'section' in key.lower() and str(val).isdigit():
                    section_id = int(val)
                if 'path' in key.lower() and str(val).isdigit():
                    learning_path_id = int(val)

        # 2. Fallback: Moodle DB
        if resource_id and (not section_id or not learning_path_id):
            try:
                
                inqiry_course_query = "SELECT section FROM mdl_course_modules WHERE id = %s"
                params = (resource_id,)
                res = self.db.inquiry_query(inqiry_course_query, params)
                
                if res:
                    section_id = res[0]['section']

                # mysql_conn = self.db_manager.get_mysql_connection()
                # with mysql_conn.cursor() as mysql_cursor:
                #     if not section_id:
                #         mysql_cursor.execute("SELECT section FROM mdl_course_modules WHERE id = %s", (resource_id,))
                #         res = mysql_cursor.fetchone()
                #         if res: section_id = res['section']
                    
                    # if not learning_path_id:
                    #     mysql_cursor.execute("SELECT competencyid FROM mdl_competency_modulecomp WHERE cmid = %s", (resource_id,))
                    #     comp_res = mysql_cursor.fetchone()
                    #     if comp_res:
                    #         comp_id = comp_res['competencyid']
                    #         actor_name = statement.actor.account.name if statement.actor and statement.actor.account else None
                    #         if actor_name:
                    #             mysql_cursor.execute("""
                    #                 SELECT p.id FROM mdl_competency_plan p
                    #                 JOIN mdl_competency_plancomp pc ON p.id = pc.planid
                    #                 JOIN mdl_user u ON p.userid = u.id
                    #                 WHERE (u.username = %s OR u.id = %s) AND pc.competencyid = %s
                    #             """, (actor_name, actor_name, comp_id))
                    #             plan_res = mysql_cursor.fetchone()
                    #             if plan_res: learning_path_id = plan_res['id']

            except Exception as e:
                logger.error(f"Error fetching section/path from Moodle: {e}")

        # 3. Generate Composite context_id (e.g., CTX_12_90_273)
        c_id_part = str(course_id) if course_id else "0"
        s_id_part = str(section_id) if section_id else "0"
        r_id_part = str(resource_id) if resource_id else "0"
        context_id = f"CTX_{c_id_part}_{s_id_part}_{r_id_part}"
        
        self.contextId = context_id
        
        return {
            "context_id": context_id,
            "section_id": section_id,
            "course_id":  course_id,
            "resource_id": resource_id,
            "learning_path_id": learning_path_id,
        }