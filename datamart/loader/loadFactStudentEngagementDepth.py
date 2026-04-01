from utils.pgsql_utils import db

class LoadFactStudentEngagementDepth:
    """
    Enhanced Engagement Depth Classification based on REAL Behavior Patterns
    
    Philosophy:
    - Deep Dive: Moderate interactions + Completion + Varied activities
    - Stuck: Many interactions + No completion + Repetitive pattern
    - Skimming: Few interactions + Quick exits
    - Normal: Average interactions + Some completion
    
    Key Indicators:
    1. Interaction Count (relative to class)
    2. Completion Status (did they finish?)
    3. Interaction Pattern (varied vs repetitive)
    4. Time Span (quick vs extended)
    """
    
    def __init__(self):
        self.dm = "datamart"
        self.dw = "datawarehouse"

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_engagement_depth;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_student_engagement_depth (
                student_key, course_key, resource_key, 
                depth_ratio, engagement_type
            )
            WITH 
            -- Step 1: Calculate class-wide statistics per resource
            class_stats AS (
                SELECT 
                    context_id,
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY interaction_count) as median_interactions,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY interaction_count) as p75_interactions,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY interaction_count) as p25_interactions
                FROM (
                    SELECT context_id, actor_id, COUNT(*) as interaction_count
                    FROM {self.dw}.fact_activity
                    GROUP BY context_id, actor_id
                ) t
                GROUP BY context_id
            ),
            
            -- Step 2: Get completion status per student-resource from fact_quiz
            completion_status AS (
                SELECT 
                    q.actor_id,
                    q.context_id,
                    MAX(CASE WHEN q.completion_status = TRUE THEN 1 ELSE 0 END) as is_completed
                FROM {self.dw}.fact_quiz q
                GROUP BY q.actor_id, q.context_id
            ),
            
            -- Step 3: Calculate interaction patterns
            student_resource_metrics AS (
                SELECT 
                    a.actor_id,
                    c.course_id,
                    c.resource_id,
                    c.context_id,
                    COUNT(a.activity_id) as interaction_count,
                    COUNT(DISTINCT a.activity_type) as activity_variety,
                    -- Note: time_span calculation removed - dim_time doesn't have timestamp
                    -- Completion status
                    COALESCE(comp.is_completed, 0) as is_completed
                FROM {self.dw}.fact_activity a
                JOIN {self.dw}.dim_context c ON a.context_id = c.context_id
                LEFT JOIN completion_status comp ON 
                    a.actor_id = comp.actor_id AND 
                    c.context_id = comp.context_id
                WHERE c.resource_id IS NOT NULL
                GROUP BY a.actor_id, c.course_id, c.resource_id, c.context_id, comp.is_completed
            ),
            
            -- Step 4: Calculate depth ratio and classify
            classified AS (
                SELECT 
                    srm.actor_id as student_key,
                    CAST(srm.course_id AS VARCHAR) as course_key,
                    CAST(srm.resource_id AS VARCHAR) as resource_key,
                    srm.interaction_count,
                    cs.median_interactions,
                    cs.p75_interactions,
                    cs.p25_interactions,
                    srm.activity_variety,
                    srm.is_completed,
                    -- Depth ratio (relative to class median)
                    ROUND(
                        (CAST(srm.interaction_count AS NUMERIC) / 
                        GREATEST(cs.median_interactions, 1))::NUMERIC, 
                        2
                    ) as depth_ratio,
                    
                    -- Classification logic based on multiple factors
                    CASE 
                        -- SKIMMING: Very few interactions, quick exit
                        -- < 50% of class median OR < 3 interactions total
                        WHEN srm.interaction_count < GREATEST(cs.median_interactions * 0.5, 3) 
                        THEN 'Skimming'
                        
                        -- STUCK: Many interactions but no completion
                        -- > 150% of class median AND not completed AND low variety
                        WHEN srm.interaction_count > cs.p75_interactions * 1.2
                             AND srm.is_completed = 0
                             AND srm.activity_variety <= 2
                        THEN 'Stuck'
                        
                        -- DEEP DIVE: Good interactions with completion or variety
                        -- Between 75%-150% of median AND (completed OR high variety)
                        WHEN srm.interaction_count >= cs.median_interactions * 0.75
                             AND srm.interaction_count <= cs.p75_interactions * 1.2
                             AND (srm.is_completed = 1 OR srm.activity_variety >= 3)
                        THEN 'Deep Dive'
                        
                        -- DEEP DIVE (Alternative): High interactions with completion
                        -- > 150% of median BUT completed (not stuck, just thorough)
                        WHEN srm.interaction_count > cs.p75_interactions * 1.2
                             AND srm.is_completed = 1
                        THEN 'Deep Dive'
                        
                        -- NORMAL: Everything else (average behavior)
                        ELSE 'Normal'
                    END as engagement_type
                    
                FROM student_resource_metrics srm
                JOIN class_stats cs ON srm.context_id = cs.context_id
            )
            
            SELECT 
                student_key,
                course_key,
                resource_key,
                depth_ratio,
                engagement_type
            FROM classified;
        """
        
        db.execute_query(insert_query)