import logging
from utils.dataExtractorUtils import DataExtractor
from utils.moodle_db_utils import moodle_db

logger = logging.getLogger(__name__)

class transformFactQuestion:
    def __init__(self):
        self.db = moodle_db


    def _generate_quiz_attempt_id(self, statement) -> str:
        """Generate a unique quiz_attempt_id from registration + quiz cmid"""
        registration = statement.context.registration if statement.context else "no_reg"
        cmid = DataExtractor.extract_moodle_module_id(statement.object.id)
        
        if cmid:
            raw = f"{registration}_{cmid}"
        else:
            raw = f"{registration}_{statement.object.id}"
            
        return str(DataExtractor.normalize_uuid(raw))

    def _get_quiz_metadata(self, cmid, actor_id):
        """Fetch max_score, attempt_no, quiz_id and attempt_id from Moodle"""
        max_score = None
        attempt_no = None
        quiz_id = None
        attempt_id = None
        
        if not cmid:
            return None, None, None, None
            
        try:
            
            get_quiz_instance_id_query = """
                    SELECT cm.instance as quiz_id, q.grade as max_score
                    FROM mdl_course_modules cm
                    JOIN mdl_quiz q ON q.id = cm.instance
                    WHERE cm.id = %s
                """
            params = (cmid,)
            res = self.db.inquiry_query(get_quiz_instance_id_query, params)

            if res:
                # max_score = res['max_score']
                quiz_id = res[0]['quiz_id']
                if actor_id:
                    get_attempt_info_query = """
                            SELECT id as attempt_id, attempt as attempt_no 
                            FROM mdl_quiz_attempts 
                            WHERE quiz = %s AND userid = (
                                SELECT id FROM mdl_user WHERE username = %s OR id = %s
                            )
                            ORDER BY attempt DESC LIMIT 1
                        """
                    params = (quiz_id, actor_id, actor_id)
                    att_res = self.db.inquiry_query(get_attempt_info_query, params)
                    
                    if att_res:
                        attempt_id = att_res[0]['attempt_id']
                        attempt_no = att_res[0]['attempt_no']


            # mysql_conn = self.db_manager.get_mysql_connection()
            # with mysql_conn.cursor() as mysql_cursor:
            #     # Get quiz instance ID and max grade
            #     mysql_cursor.execute("""
                    
            #     """, (cmid,))
            #     res = mysql_cursor.fetchone()
                
            #     if res:
            #         max_score = res['max_score']
            #         quiz_id = res['quiz_id']
                    
            #         # Get attempt info for this user
            #         if actor_id:
            #             mysql_cursor.execute("""
            #                 SELECT id as attempt_id, attempt as attempt_no 
            #                 FROM mdl_quiz_attempts 
            #                 WHERE quiz = %s AND userid = (
            #                     SELECT id FROM mdl_user WHERE username = %s OR id = %s
            #                 )
            #                 ORDER BY attempt DESC LIMIT 1
            #             """, (quiz_id, actor_id, actor_id))
            #             att_res = mysql_cursor.fetchone()
            #             if att_res:
            #                 attempt_id = att_res['attempt_id']
            #                 attempt_no = att_res['attempt_no']
                            
        except Exception as e:
            logger.error(f"Error fetching quiz metadata from Moodle: {e}")
        
        return max_score, attempt_no, quiz_id, attempt_id

    
    def transform(self, statement, kwargs = {}):
        if 'answered' not in statement.verb.id.lower() or not statement.context or not statement.context.registration:
            return {}
        
        # Only process quiz questions (usually contain 'question' or 'quiz')
        obj_id = statement.object.id.lower()
        if 'quiz' not in obj_id and 'question' not in obj_id:
            return {}
            
        question_id = statement.object.id
        actor_id = statement.actor.account.name if statement.actor.account else None
        
        # 1. Generate quiz_attempt_id
        m_attempt_id = DataExtractor.extract_moodle_attempt_id(statement)
        if m_attempt_id:
            quiz_attempt_id = str(m_attempt_id)
        else:
            quiz_attempt_id = self._generate_quiz_attempt_id(statement)
            
        # 2. Extract metadata for the parent quiz
        cmid = DataExtractor.extract_moodle_module_id(statement.object.id)
        max_score, attempt_no, quiz_id, m_attempt_id2 = self._get_quiz_metadata(cmid, actor_id)
        
        # Map quiz_attempt_id to Moodle attempt id if available
        if m_attempt_id2:
            quiz_attempt_id = str(m_attempt_id2)
        
        # 3. Ensure parent quiz exists (Rich Upsert)
        start_time = DataExtractor.parse_timestamp(statement.timestamp)
        
        selected_answer = None
        is_correct = None
        if statement.result:
            selected_answer = statement.result.response
            if statement.result.extensions and "http://learninglocker.net/xapi/cmi/choice/response" in statement.result.extensions:
                selected_answer = statement.result.extensions["http://learninglocker.net/xapi/cmi/choice/response"]
            is_correct = statement.result.success

        return {
            "question_id": question_id,
            "quiz_attempt_id": quiz_attempt_id,
            "quiz_id": quiz_id,
            "start_time": start_time,
            "selected_answer": selected_answer,
            "attempt_no": attempt_no,
            "is_correct": is_correct,
        }