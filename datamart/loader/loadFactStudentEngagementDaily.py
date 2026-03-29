from utils.pgsql_utils import db

class LoadFactStudentEngagementDailyV2:
    """
    Enhanced Engagement Score Calculation based on REAL Student Behavior
    
    Reality-Based Philosophy:
    - Students don't study every day → Score based on activity days only
    - xAPI doesn't track actual study time → Focus on interaction quality
    - Quizzes are periodic, not daily → Bonus when done, not penalty when not
    - Quality matters: Deep learning > Quick clicks
    - Frequency matters: More interactions = More engagement
    
    Key Changes from V2:
    - NO TIME SCORE (xAPI duration is unreliable - just timestamp diffs)
    - Resource Score: 70 points (main component, quality-weighted)
    - Quiz Bonus: 30 points (bonus when available)
    - Frequency bonus: Reward consistent daily interactions
    """
    
    def __init__(self):
        self.dw = "datawarehouse"
        self.datamart_name = "datamart"

    def load(self):
        # Full refresh (commented out - incremental update instead)
        # db.execute_query(f"TRUNCATE TABLE {self.datamart_name}.fact_daily_student_engagement;")

        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_daily_student_engagement (
                student_key, course_key, date_key,
                total_resource_access,
                total_quiz_attempt, 
                total_active_minutes,
                engagement_score
            )
            WITH 
            -- Step 1: Get resource metadata (mandatory vs optional)
            resource_metadata AS (
                SELECT 
                    c.context_id,
                    c.resource_id,
                    c.course_id,
                    COALESCE(a.is_mandatory, false) as is_mandatory
                FROM {self.dw}.dim_context c
                LEFT JOIN {self.dw}.fact_activity a ON c.context_id = a.context_id
                WHERE c.resource_id IS NOT NULL
                GROUP BY c.context_id, c.resource_id, c.course_id, a.is_mandatory
            ),
            
            -- Step 2: Calculate engagement depth per resource (from existing fact)
            engagement_depth AS (
                SELECT 
                    student_key,
                    course_key,
                    resource_key,
                    engagement_type,
                    depth_ratio
                FROM {self.datamart_name}.fact_student_engagement_depth
            ),
            
            -- Step 3: Daily activity with quality scoring
            activity_daily AS (
                SELECT
                    a.actor_id,
                    c.course_id,
                    a.time_id,
                    c.resource_id,
                    COUNT(a.activity_id) AS interaction_count,
                    -- Quality multiplier based on engagement depth (INCREASED WEIGHT)
                    CASE 
                        WHEN ed.engagement_type = 'Deep Dive' THEN 2.0   -- Reward deep learning heavily
                        WHEN ed.engagement_type = 'Stuck' THEN 1.2       -- Effort counts, even if struggling
                        WHEN ed.engagement_type = 'Skimming' THEN 0.4    -- Penalize superficial learning
                        ELSE 1.0
                    END as quality_multiplier,
                    -- Importance multiplier (REDUCED - not too harsh)
                    CASE 
                        WHEN rm.is_mandatory THEN 1.3
                        ELSE 1.0
                    END as importance_multiplier
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                LEFT JOIN resource_metadata rm ON c.context_id = rm.context_id
                LEFT JOIN engagement_depth ed ON 
                    a.actor_id = ed.student_key AND 
                    CAST(c.course_id AS VARCHAR) = ed.course_key AND
                    CAST(c.resource_id AS VARCHAR) = ed.resource_key
                WHERE c.course_id IS NOT NULL
                GROUP BY a.actor_id, c.course_id, a.time_id, c.resource_id, 
                         ed.engagement_type, rm.is_mandatory
            ),
            
            -- Step 4: Aggregate activity with weighted scoring
            activity_aggregated AS (
                SELECT
                    actor_id,
                    course_id,
                    time_id,
                    COUNT(DISTINCT resource_id) AS unique_resources_accessed,
                    SUM(interaction_count) AS total_interactions,
                    -- Base resource score (0-50 points)
                    -- Average student accessing 3-5 resources should get ~30 points
                    -- Base resource score (0-70 points) - MAIN COMPONENT
                    -- Average student accessing 3-5 resources should get ~40-50 points
                    LEAST(
                        SUM(
                            LEAST(interaction_count, 3) * -- Cap at 3 interactions per resource (realistic)
                            quality_multiplier * 
                            importance_multiplier * 
                            3.0  -- Scale factor (increased from 2.0)
                        ),
                        70
                    ) AS weighted_resource_score
                FROM activity_daily
                GROUP BY actor_id, course_id, time_id
            ),
            
            -- Step 5: Quiz performance as BONUS (not required)
            quiz_daily AS (
                SELECT
                    q.actor_id,
                    c.course_id,
                    q.time_id,
                    COUNT(DISTINCT q.quiz_id) AS unique_quizzes_attempted,
                    COUNT(q.quiz_attempt_id) AS total_quiz_attempts,
                    -- Quiz BONUS score (0-30 points)
                    -- This is a bonus, not required for good engagement
                    -- Since we don't have max_score, use score directly with scaling
                    LEAST(
                        SUM(
                            CASE 
                                -- High score (>=9): 15 points bonus
                                WHEN q.score >= 9 THEN 15
                                -- Good score (>=7): 12 points
                                WHEN q.score >= 7 THEN 12
                                -- Pass score (>=5): 8 points
                                WHEN q.score >= 5 THEN 8
                                -- Attempted but low score: 4 points (effort counts)
                                WHEN q.score > 0 THEN 4
                                -- No score recorded: 2 points for attempt
                                ELSE 2
                            END
                        ),
                        30
                    ) AS quiz_bonus_score
                FROM {self.dw}.fact_quiz q
                JOIN {self.dw}.dim_context c ON q.context_id = c.context_id
                WHERE c.course_id IS NOT NULL
                GROUP BY q.actor_id, c.course_id, q.time_id
            ),

            
            -- Step 6: Combine all metrics
            combined AS (
                SELECT
                    COALESCE(aa.actor_id, qd.actor_id) AS actor_id,
                    COALESCE(aa.course_id, qd.course_id) AS course_id,
                    COALESCE(aa.time_id, qd.time_id) AS time_id,
                    COALESCE(aa.unique_resources_accessed, 0) AS unique_resources,
                    COALESCE(aa.total_interactions, 0) AS total_resource_access,
                    COALESCE(qd.total_quiz_attempts, 0) AS total_quiz_attempt,
                    COALESCE(aa.weighted_resource_score, 0) AS resource_score,
                    COALESCE(qd.quiz_bonus_score, 0) AS quiz_bonus
                FROM activity_aggregated aa
                FULL OUTER JOIN quiz_daily qd
                    ON aa.actor_id = qd.actor_id 
                    AND aa.course_id = qd.course_id 
                    AND aa.time_id = qd.time_id
            )
            
            -- Step 7: Calculate final engagement score (REALISTIC - NO TIME)
            SELECT
                co.actor_id AS student_key,
                CAST(co.course_id AS INT) AS course_key,
                co.time_id AS date_key,
                co.total_resource_access,
                co.total_quiz_attempt,
                0 AS total_active_minutes,  -- Not reliable from xAPI
                
                -- FINAL ENGAGEMENT SCORE (0-100) - REALISTIC VERSION
                -- 
                -- Base Score (70 points max):
                --   70 points: Resource interaction (quality-weighted)
                --
                -- Bonus (30 points max):
                --   30 points: Quiz performance (when available)
                --
                -- Philosophy:
                --   - xAPI doesn't track actual study time (only event timestamps)
                --   - Focus on WHAT students do, not HOW LONG
                --   - Quality of interaction matters most
                --   - Can get 70/100 without quiz (Good engagement)
                --   - Quiz is bonus to reach Excellent (80-100)
                --
                -- Why no time score:
                --   - session_duration = last_event - first_event (includes idle time)
                --   - Students may open tab and do other things
                --   - Not accurate measure of actual learning time
                --
                LEAST(
                    ROUND(
                        co.resource_score +      -- 0-70 points (main component)
                        co.quiz_bonus            -- 0-30 points (bonus when available)
                    )::INT,
                    100
                ) AS engagement_score
                
            FROM combined co
            WHERE co.actor_id IS NOT NULL 
              AND co.course_id IS NOT NULL 
              AND co.time_id IS NOT NULL
              -- ONLY score days with actual activity
              AND (co.resource_score > 0 OR co.quiz_bonus > 0);
        """
        
        db.execute_query(insert_query)
        print("✅ Successfully loaded FactStudentEngagementDaily V2 (Realistic - No Time).")
        print("📊 Realistic Scoring Breakdown:")
        print("   - Resource Interaction: 70 points (quality-weighted, main component)")
        print("   - Quiz Bonus: 30 points (bonus when available, not required)")
        print("   - Total: 100 points max")
        print("")
        print("⚠️  Why NO time score:")
        print("   - xAPI only has timestamps, not actual study time")
        print("   - session_duration = last_event - first_event (includes idle)")
        print("   - Not accurate for measuring real learning time")
        print("")
        print("🎯 Focus on WHAT students do, not HOW LONG:")
        print("   - Deep learning > Quick clicks")
        print("   - Quality > Quantity")
        print("   - Quiz is bonus, not requirement")
        print("   - Only score days with activity")
