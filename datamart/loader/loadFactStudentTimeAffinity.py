"""
Load Fact Student Time Affinity V2

This V2 loader adds contextual interpretation and actionable insights to time affinity metrics.

Fixes Bug 3: Time Affinity Metric
- Adds student average calculation for comparison
- Adds relative performance metric
- Adds peak time identification
- Adds interpretation field for teachers
- Adds recommendation field with actionable insights
"""

from utils.pgsql_utils import db


class LoadFactStudentTimeAffinity:
    def __init__(self):
        self.dm = "datamart"

    def load(self):
        db.execute_query(f"TRUNCATE TABLE {self.dm}.fact_student_time_affinity;")

        insert_query = f"""
            INSERT INTO {self.dm}.fact_student_time_affinity (
                student_key, course_key, time_slot, 
                efficiency_index, total_engagement_score, session_count,
                student_avg_efficiency, relative_efficiency, is_peak_time, peak_rank,
                interpretation, recommendation
            )
            WITH BaseMetrics AS (
                -- Calculate base efficiency metrics per time slot
                SELECT 
                    f.student_key,
                    CAST(f.course_key AS VARCHAR) as course_key,
                    t.time_slot,
                    ROUND(CAST(SUM(f.engagement_score) AS NUMERIC) / GREATEST(COUNT(DISTINCT f.date_key), 1), 2) as efficiency_index,
                    SUM(f.engagement_score) as total_engagement_score,
                    COUNT(DISTINCT f.date_key) as session_count
                FROM {self.dm}.fact_daily_student_engagement f
                JOIN {self.dm}.dim_time t ON f.date_key = t.time_id
                GROUP BY f.student_key, f.course_key, t.time_slot
            ),
            StudentAverage AS (
                -- Calculate each student's average efficiency across all time slots
                SELECT 
                    student_key,
                    course_key,
                    ROUND(AVG(efficiency_index), 2) as student_avg_efficiency
                FROM BaseMetrics
                GROUP BY student_key, course_key
            ),
            PeakIdentification AS (
                -- Identify peak productivity times for each student
                SELECT 
                    bm.student_key,
                    bm.course_key,
                    bm.time_slot,
                    bm.efficiency_index,
                    ROW_NUMBER() OVER (
                        PARTITION BY bm.student_key, bm.course_key 
                        ORDER BY bm.efficiency_index DESC
                    ) as peak_rank,
                    CASE 
                        WHEN ROW_NUMBER() OVER (
                            PARTITION BY bm.student_key, bm.course_key 
                            ORDER BY bm.efficiency_index DESC
                        ) = 1 THEN TRUE
                        ELSE FALSE
                    END as is_peak_time
                FROM BaseMetrics bm
            )
            SELECT 
                bm.student_key,
                bm.course_key,
                bm.time_slot,
                bm.efficiency_index,
                bm.total_engagement_score,
                bm.session_count,
                
                -- V2: Student average for comparison
                sa.student_avg_efficiency,
                
                -- V2: Relative performance metric
                CASE 
                    WHEN sa.student_avg_efficiency > 0 THEN
                        ROUND((bm.efficiency_index / sa.student_avg_efficiency * 100)::NUMERIC, 2)
                    ELSE 100
                END as relative_efficiency,
                
                -- V2: Peak time identification
                pi.is_peak_time,
                pi.peak_rank,
                
                -- V2: Interpretation field
                CASE 
                    WHEN sa.student_avg_efficiency > 0 AND 
                         (bm.efficiency_index / sa.student_avg_efficiency * 100) >= 120 THEN
                        'Peak Productivity - Ideal for interventions'
                    WHEN sa.student_avg_efficiency > 0 AND 
                         (bm.efficiency_index / sa.student_avg_efficiency * 100) >= 100 THEN
                        'Above Average - Good study time'
                    WHEN sa.student_avg_efficiency > 0 AND 
                         (bm.efficiency_index / sa.student_avg_efficiency * 100) >= 80 THEN
                        'Average - Acceptable study time'
                    ELSE
                        'Below Average - Consider alternative times'
                END as interpretation,
                
                -- V2: Recommendation field
                CASE 
                    WHEN pi.is_peak_time = TRUE THEN
                        'Schedule important tasks and interventions during this time'
                    WHEN sa.student_avg_efficiency > 0 AND 
                         (bm.efficiency_index / sa.student_avg_efficiency * 100) < 80 THEN
                        'Encourage shifting study to higher-productivity times'
                    WHEN sa.student_avg_efficiency > 0 AND 
                         ABS((bm.efficiency_index / sa.student_avg_efficiency * 100) - 100) < 10 THEN
                        'Consistent performance - Maintain current study patterns'
                    ELSE
                        'Monitor and adjust study schedule as needed'
                END as recommendation
                
            FROM BaseMetrics bm
            JOIN StudentAverage sa 
                ON bm.student_key = sa.student_key 
                AND bm.course_key = sa.course_key
            JOIN PeakIdentification pi 
                ON bm.student_key = pi.student_key 
                AND bm.course_key = pi.course_key 
                AND bm.time_slot = pi.time_slot;
        """
        db.execute_query(insert_query)