import logging
from utils.dataExtractorUtils import DataExtractor
from utils.moodle_db_utils import moodle_db

logger = logging.getLogger(__name__)


class transformFactQuiz:
    def __init__(self):
        self.db = moodle_db
    

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

    def _generate_quiz_attempt_id(self, statement) -> str:
        """Generate a unique quiz_attempt_id from registration + quiz cmid"""
        registration = statement.context.registration if statement.context else "no_reg"
        cmid = DataExtractor.extract_moodle_module_id(statement.object.id)
        
        # User requested explicitly: combine registration + cmid
        if cmid:
            raw = f"{registration}_{cmid}"
        else:
            # Fallback if cmid is missing
            raw = f"{registration}_{statement.object.id}"
            
        return str(DataExtractor.normalize_uuid(raw))



    def transform(self, statement, kwargs = {}):
        """Process fact_quiz for quiz-related verbs (completed/passed/failed/started)"""
        verb_id = statement.verb.id.lower()
        object_id = statement.object.id.lower()
        
        # Only process quiz-related statements
        if 'quiz' not in object_id:
            return {}
             
        is_completion = any(v in verb_id for v in ['completed', 'passed', 'failed'])
        is_start = 'start' in verb_id
        
        if not is_completion and not is_start:
            return {}
            
        if not statement.context or not statement.context.registration:
            return {}
            
        quiz_attempt_id = DataExtractor.extract_moodle_attempt_id(statement)
        if quiz_attempt_id:
            quiz_attempt_id = str(quiz_attempt_id)
        else:
            quiz_attempt_id = self._generate_quiz_attempt_id(statement)

        actor_id = statement.actor.account.name if statement.actor.account else None
        timestamp = DataExtractor.parse_timestamp(statement.timestamp)
        cmid = DataExtractor.extract_moodle_module_id(statement.object.id)
        
        # Extract result data
        total_score = None
        is_complete = None
        is_succeed = None
        duration = None
        
        if statement.result:
            if statement.result.score:
                total_score = statement.result.score.raw
            if statement.result.completion is not None:
                is_complete = statement.result.completion
            if statement.result.success is not None:
                is_succeed = statement.result.success
            duration = DataExtractor.parse_duration(statement.result.duration)

        # Refine flags based on verb if missing
        if 'completed' in verb_id and is_complete is None: is_complete = True
        if 'passed' in verb_id and is_succeed is None: is_succeed = True
        if 'failed' in verb_id and is_succeed is None: is_succeed = False

        # Fetch max_score, attempt_no, quiz_id, and attempt_id from Moodle
        max_score, attempt_no, quiz_id, m_attempt_id = self._get_quiz_metadata(cmid, actor_id)

        # Map quiz_attempt_id to Moodle attempt id if available
        if m_attempt_id:
            quiz_attempt_id = str(m_attempt_id)

        time_id = kwargs.get("time_id", "")
        return {
            "quiz_attempt_id": quiz_attempt_id,
            "quiz_id": quiz_id,
            "attempt_no": attempt_no,
            "actor_id": actor_id,
            "start_time": timestamp,
            "end_time": timestamp,
            "score": total_score,
            "duration": duration,
            "completion_status": is_complete,
            "isSucceed": is_succeed,
            "time_id": time_id,
            "context_id": kwargs.get("context_id", "")
        }