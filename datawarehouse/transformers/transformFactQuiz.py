import re
import logging
from utils.dataExtractorUtils import DataExtractor
from utils.moodle_db_utils import moodle_db

logger = logging.getLogger(__name__)


class transformFactQuiz:
    def __init__(self):
        self.db = moodle_db
    

    def _extract_attempt_from_xapi(self, statement) -> tuple:
        """
        Extract attempt_no and attempt_id from xAPI statement URLs
        
        Priority:
        1. Extract from object.id (main URL)
        2. Extract from contextActivities (parent, grouping, etc.)
        
        Returns: (attempt_id, attempt_no)
        """
        attempt_id = None
        attempt_no = None
        
        # Collect all URLs to check
        urls = [statement.object.id]
        if statement.context and statement.context.contextActivities:
            ca = statement.context.contextActivities
            for attr in ['parent', 'grouping', 'category', 'other']:
                activities = getattr(ca, attr, None)
                if activities:
                    urls.extend([p.id for p in activities])
        
        # Try to extract attempt from URLs
        for url in urls:
            # Pattern 1: attempt=123
            match = re.search(r'attempt[=:](\d+)', url, re.IGNORECASE)
            if match:
                attempt_id = int(match.group(1))
                # If we find attempt in URL, we can infer attempt_no
                # Usually attempt_id in Moodle corresponds to the attempt number
                # But we'll try to get the actual attempt_no from Moodle later
                break
        
        return attempt_id, attempt_no
    
    def _get_quiz_metadata(self, cmid, actor_id, statement=None):
        """
        Fetch max_score, attempt_no, quiz_id and attempt_id
        
        Priority:
        1. Extract attempt_id from xAPI statement (fast, no DB query)
        2. Query Moodle database (fallback)
        """
        max_score = None
        attempt_no = None
        quiz_id = None
        attempt_id = None
        
        # STEP 1: Try to extract attempt from xAPI first
        if statement:
            xapi_attempt_id, xapi_attempt_no = self._extract_attempt_from_xapi(statement)
            if xapi_attempt_id:
                attempt_id = xapi_attempt_id
                logger.debug(f"Extracted attempt_id from xAPI: {attempt_id}")
        
        if not cmid:
            return None, None, None, attempt_id
            
        try:
            # STEP 2: Get quiz_id from cmid
            get_quiz_instance_id_query = """
                    SELECT cm.instance as quiz_id, q.grade as max_score
                    FROM mdl_course_modules cm
                    JOIN mdl_quiz q ON q.id = cm.instance
                    WHERE cm.id = %s
                """
            params = (cmid,)
            res = self.db.inquiry_query(get_quiz_instance_id_query, params)

            if res:
                quiz_id = res[0]['quiz_id']
                
                # STEP 3: If we have attempt_id from xAPI, get attempt_no from Moodle
                if attempt_id and actor_id:
                    get_attempt_no_query = """
                            SELECT attempt as attempt_no 
                            FROM mdl_quiz_attempts 
                            WHERE id = %s AND quiz = %s
                        """
                    params = (attempt_id, quiz_id)
                    att_res = self.db.inquiry_query(get_attempt_no_query, params)
                    
                    if att_res:
                        attempt_no = att_res[0]['attempt_no']
                        logger.debug(f"Got attempt_no from Moodle: {attempt_no}")
                
                # STEP 4: Fallback - Query by actor_id if no attempt_id from xAPI
                elif actor_id and not attempt_id:
                    # Try to convert actor_id to int for numeric comparison
                    try:
                        actor_id_int = int(actor_id)
                        get_attempt_info_query = """
                                SELECT id as attempt_id, attempt as attempt_no 
                                FROM mdl_quiz_attempts 
                                WHERE quiz = %s AND userid IN (
                                    SELECT id FROM mdl_user 
                                    WHERE username = %s 
                                       OR id = %s
                                       OR id = %s
                                )
                                ORDER BY attempt DESC LIMIT 1
                            """
                        params = (quiz_id, actor_id, actor_id, actor_id_int)
                    except (ValueError, TypeError):
                        # actor_id is not numeric, only try username match
                        get_attempt_info_query = """
                                SELECT id as attempt_id, attempt as attempt_no 
                                FROM mdl_quiz_attempts 
                                WHERE quiz = %s AND userid IN (
                                    SELECT id FROM mdl_user 
                                    WHERE username = %s 
                                       OR id = %s
                                )
                                ORDER BY attempt DESC LIMIT 1
                            """
                        params = (quiz_id, actor_id, actor_id)
                    
                    att_res = self.db.inquiry_query(get_attempt_info_query, params)
                    
                    if att_res:
                        attempt_id = att_res[0]['attempt_id']
                        attempt_no = att_res[0]['attempt_no']
                        logger.debug(f"Got attempt from Moodle query: id={attempt_id}, no={attempt_no}")


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

        # Fetch max_score, attempt_no, quiz_id, and attempt_id
        # Priority: xAPI extraction first, then Moodle query
        max_score, attempt_no, quiz_id, m_attempt_id = self._get_quiz_metadata(cmid, actor_id, statement)

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