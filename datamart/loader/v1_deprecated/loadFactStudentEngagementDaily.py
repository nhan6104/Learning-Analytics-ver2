from utils.pgsql_utils import db

class LoadFactStudentEngagementDaily:
    def __init__(self):
        self.dw = "datawarehouse"
        self.datamart_name = "datamart"

    def load(self):
        # Full refresh
        db.execute_query(f"TRUNCATE TABLE {self.datamart_name}.fact_daily_student_engagement;")

        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_daily_student_engagement (
                student_key, course_key, date_key,
                total_resource_access,
                total_quiz_attempt, 
                total_active_minutes,
                engagement_score
            )
            WITH activity_daily AS (
                -- Total resource accesses per actor, course, day
                SELECT
                    a.actor_id,
                    c.course_id,
                    a.time_id,
                    COUNT(a.activity_id) AS total_resource_access
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
                GROUP BY a.actor_id, c.course_id, a.time_id
            ),
            quiz_daily AS (
                -- Total quiz attempts per actor, course, day
                SELECT
                    q.actor_id,
                    c.course_id,
                    q.time_id,
                    COUNT(q.quiz_attempt_id) AS total_quiz_attempt
                FROM {self.dw}.fact_quiz q
                JOIN {self.dw}.dim_context c ON q.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
                GROUP BY q.actor_id, c.course_id, q.time_id
            ),
            session_daily AS (
                -- Total active minutes per actor, course, day
                SELECT
                    s.actor_id,
                    c.course_id,
                    s.time_id,
                    ROUND(SUM(s.session_duration) / 60.0) AS total_active_minutes
                FROM {self.dw}.fact_session s
                JOIN {self.dw}.dim_context c ON s.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
                GROUP BY s.actor_id, c.course_id, s.time_id
            ),
            combined AS (
                SELECT
                    COALESCE(ad.actor_id, qd.actor_id, sd.actor_id) AS actor_id,
                    COALESCE(ad.course_id, qd.course_id, sd.course_id) AS course_id,
                    COALESCE(ad.time_id, qd.time_id, sd.time_id) AS time_id,
                    COALESCE(ad.total_resource_access, 0) AS total_resource_access,
                    COALESCE(qd.total_quiz_attempt, 0) AS total_quiz_attempt,
                    COALESCE(sd.total_active_minutes, 0) AS total_active_minutes
                FROM activity_daily ad
                FULL OUTER JOIN quiz_daily qd
                    ON ad.actor_id = qd.actor_id AND ad.course_id = qd.course_id AND ad.time_id = qd.time_id
                FULL OUTER JOIN session_daily sd
                    ON COALESCE(ad.actor_id, qd.actor_id) = sd.actor_id 
                    AND COALESCE(ad.course_id, qd.course_id) = sd.course_id 
                    AND COALESCE(ad.time_id, qd.time_id) = sd.time_id
            )
            SELECT
                co.actor_id AS student_key,
                CAST(co.course_id AS INT) AS course_key,
                co.time_id AS date_key,
                co.total_resource_access,
                co.total_quiz_attempt,
                co.total_active_minutes,
                -- engagement_score: dynamic scale based on course density (20% resources + 1 Quiz = 100 pts)
                ROUND(
                    LEAST(co.total_resource_access, GREATEST(5, CAST(COALESCE(dc.total_modules, 50) * 0.2 AS INT))) * 
                    (50.0 / GREATEST(5, CAST(COALESCE(dc.total_modules, 50) * 0.2 AS INT))) +
                    LEAST(co.total_quiz_attempt, 1) * 50
                ) AS engagement_score
            FROM combined co
            LEFT JOIN {self.datamart_name}.dim_course dc ON co.course_id = dc.course_key
            WHERE co.actor_id IS NOT NULL AND co.course_id IS NOT NULL AND co.time_id IS NOT NULL;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactStudentEngagementDaily.")