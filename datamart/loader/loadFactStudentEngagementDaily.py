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
                total_active_minutes, total_resource_access,
                total_quiz_attempt, engagement_score, active_learning_index
            )
            WITH session_daily AS (
                -- Total session duration (minutes) per actor, course, day
                SELECT
                    s.actor_id,
                    c.course_id,
                    s.time_id,
                    COALESCE(SUM(s.session_duration) / 60, 0) AS total_active_minutes
                FROM {self.dw}.fact_session s
                JOIN {self.dw}.dim_context c ON s.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
                GROUP BY s.actor_id, c.course_id, s.time_id
            ),
            activity_daily AS (
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
            combined AS (
                SELECT
                    COALESCE(sd.actor_id, ad.actor_id, qd.actor_id) AS actor_id,
                    COALESCE(sd.course_id, ad.course_id, qd.course_id) AS course_id,
                    COALESCE(sd.time_id, ad.time_id, qd.time_id) AS time_id,
                    COALESCE(sd.total_active_minutes, 0) AS total_active_minutes,
                    COALESCE(ad.total_resource_access, 0) AS total_resource_access,
                    COALESCE(qd.total_quiz_attempt, 0) AS total_quiz_attempt
                FROM session_daily sd
                FULL OUTER JOIN activity_daily ad
                    ON sd.actor_id = ad.actor_id AND sd.course_id = ad.course_id AND sd.time_id = ad.time_id
                FULL OUTER JOIN quiz_daily qd
                    ON COALESCE(sd.actor_id, ad.actor_id) = qd.actor_id
                    AND COALESCE(sd.course_id, ad.course_id) = qd.course_id
                    AND COALESCE(sd.time_id, ad.time_id) = qd.time_id
            )
            SELECT
                actor_id AS student_key,
                CAST(course_id AS INT) AS course_key,
                time_id AS date_key,
                total_active_minutes,
                total_resource_access,
                total_quiz_attempt,
                -- engagement_score: weighted sum of metrics
                (
                    LEAST(total_active_minutes, 60) * 1 +     -- max 60 pts from time
                    LEAST(total_resource_access, 20) * 1 +    -- max 20 pts from resources
                    LEAST(total_quiz_attempt, 10) * 2         -- max 20 pts from quiz
                ) AS engagement_score,
                -- active_learning_index: ratio of active activities vs total time
                CASE
                    WHEN total_active_minutes = 0 THEN 0
                    ELSE LEAST(100, (total_resource_access + total_quiz_attempt) * 100 / GREATEST(total_active_minutes, 1))
                END AS active_learning_index
            FROM combined
            WHERE actor_id IS NOT NULL AND course_id IS NOT NULL AND time_id IS NOT NULL;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactStudentEngagementDaily.")