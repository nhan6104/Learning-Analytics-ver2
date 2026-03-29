"""
Load Fact Student Risk Weekly V2

This V2 loader implements multi-factor risk calculation including:
- Weekly engagement score (30%)
- Engagement trend (25%)
- Consecutive inactivity days (20%)
- Progress lag (15%)
- Social isolation (10%)

Fixes Bug 1: Risk Score Calculation
"""

from utils.pgsql_utils import db


class LoadFactStudentRiskWeekly_v2:
    def __init__(self):
        self.datamart_name = "datamart"

    def load(self):
        # Clean up existing data for a full refresh
        delete_query = f"TRUNCATE TABLE {self.datamart_name}.fact_risk_student_weekly;"
        db.execute_query(delete_query)

        # Multi-factor risk calculation
        insert_query = f"""
            INSERT INTO {self.datamart_name}.fact_risk_student_weekly (
                student_key, course_key, week_of_year, year,
                engagement_score, progress_score, outcome_score,
                engagement_trend, inactivity_days, progress_lag_pct, social_isolation_score,
                risk_score, dropout_probability_pct, risk_level
            )
            WITH DailyAgg AS (
                -- Aggregate daily engagement to weekly
                SELECT
                    f.student_key,
                    f.course_key,
                    t.week as week_of_year,
                    t.year,
                    SUM(f.engagement_score) as weekly_engagement_score,
                    SUM(f.total_quiz_attempt) as weekly_quiz_attempts,
                    SUM(f.total_resource_access) as weekly_resource_access
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                GROUP BY f.student_key, f.course_key, t.week, t.year
            ),
            WeeklyTrend AS (
                -- Calculate 3-week moving average and trend
                SELECT
                    student_key,
                    course_key,
                    week_of_year,
                    year,
                    weekly_engagement_score,
                    AVG(weekly_engagement_score) OVER (
                        PARTITION BY student_key, course_key 
                        ORDER BY year, week_of_year 
                        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
                    ) as moving_avg_3week,
                    LAG(weekly_engagement_score, 1) OVER (
                        PARTITION BY student_key, course_key 
                        ORDER BY year, week_of_year
                    ) as prev_week_engagement,
                    weekly_quiz_attempts,
                    weekly_resource_access
                FROM DailyAgg
            ),
            InactivityTracking AS (
                -- Count consecutive days with zero engagement
                SELECT
                    f.student_key,
                    f.course_key,
                    t.week as week_of_year,
                    t.year,
                    COUNT(CASE WHEN f.engagement_score = 0 THEN 1 END) as zero_engagement_days,
                    MAX(CASE WHEN f.engagement_score > 0 THEN 
                        CAST(CONCAT(t.year, '-', LPAD(t.month::TEXT, 2, '0'), '-', LPAD(t.date::TEXT, 2, '0')) AS DATE)
                    END) as last_active_date
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                GROUP BY f.student_key, f.course_key, t.week, t.year
            ),
            ProgressLag AS (
                -- Calculate progress lag (actual vs expected)
                SELECT
                    lc.student_key,
                    lc.course_key,
                    lc.current_progress_pct,
                    -- Expected progress based on weeks elapsed
                    -- Assuming 16-week course
                    CASE 
                        WHEN lc.total_module_count > 0 THEN
                            GREATEST(0, 
                                (EXTRACT(WEEK FROM CURRENT_DATE) - 
                                 EXTRACT(WEEK FROM lc.last_activity_date)) * 6.25 - lc.current_progress_pct
                            )
                        ELSE 0
                    END as progress_lag_pct
                FROM {self.datamart_name}.fact_student_course_lifecycle lc
            ),
            SocialIsolation AS (
                -- Check for peer interactions (forum posts, group activities)
                -- This is a simplified version - adjust based on your xAPI data
                SELECT
                    f.student_key,
                    f.course_key,
                    t.week as week_of_year,
                    t.year,
                    COUNT(CASE 
                        WHEN f.total_resource_access > 0 THEN 1 
                    END) as interaction_count
                FROM {self.datamart_name}.fact_daily_student_engagement f
                JOIN {self.datamart_name}.dim_time t ON f.date_key = t.time_id
                GROUP BY f.student_key, f.course_key, t.week, t.year
            )
            SELECT
                wt.student_key,
                wt.course_key,
                wt.week_of_year,
                wt.year,
                -- Original scores
                wt.weekly_engagement_score as engagement_score,
                wt.weekly_quiz_attempts * 10 as progress_score,
                wt.weekly_resource_access * 5 as outcome_score,
                
                -- New V2 factors
                CASE 
                    WHEN wt.prev_week_engagement IS NOT NULL AND wt.prev_week_engagement > 0 THEN
                        ROUND(((wt.weekly_engagement_score - wt.prev_week_engagement) / wt.prev_week_engagement * 100)::NUMERIC, 2)
                    ELSE 0
                END as engagement_trend,
                
                COALESCE(it.zero_engagement_days, 0) as inactivity_days,
                COALESCE(pl.progress_lag_pct, 0) as progress_lag_pct,
                
                CASE 
                    WHEN COALESCE(si.interaction_count, 0) = 0 THEN 100
                    WHEN COALESCE(si.interaction_count, 0) < 3 THEN 50
                    ELSE 0
                END as social_isolation_score,
                
                -- Multi-factor risk score calculation
                LEAST(100, GREATEST(0,
                    -- Base risk (inverse of engagement) - 30%
                    (100 - wt.weekly_engagement_score) * 0.30 +
                    
                    -- Trend adjustment - 25%
                    CASE 
                        WHEN wt.prev_week_engagement IS NOT NULL THEN
                            CASE 
                                WHEN wt.weekly_engagement_score < wt.prev_week_engagement THEN 25  -- Negative trend
                                WHEN wt.weekly_engagement_score > wt.prev_week_engagement * 1.2 THEN -10  -- Positive trend
                                ELSE 0
                            END
                        ELSE 0
                    END +
                    
                    -- Inactivity penalty - 20%
                    LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) +
                    
                    -- Progress lag penalty - 15%
                    LEAST(15, COALESCE(pl.progress_lag_pct, 0) * 0.5) +
                    
                    -- Social isolation penalty - 10%
                    CASE 
                        WHEN COALESCE(si.interaction_count, 0) = 0 THEN 10
                        WHEN COALESCE(si.interaction_count, 0) < 3 THEN 5
                        ELSE 0
                    END
                ))::INTEGER as risk_score,
                
                -- Dropout probability (refined based on multi-factor risk)
                CASE 
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 70 THEN 85.0
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 50 THEN 55.0
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 30 THEN 25.0
                    ELSE 8.0
                END as dropout_probability_pct,
                
                -- Risk level classification (dynamic based on multi-factor score)
                CASE 
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 70 THEN 'Critical'
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 50 THEN 'High'
                    WHEN (100 - wt.weekly_engagement_score) * 0.30 + 
                         LEAST(20, COALESCE(it.zero_engagement_days, 0) * 3) > 30 THEN 'Medium'
                    ELSE 'Low'
                END as risk_level
                
            FROM WeeklyTrend wt
            LEFT JOIN InactivityTracking it 
                ON wt.student_key = it.student_key 
                AND wt.course_key = it.course_key
                AND wt.week_of_year = it.week_of_year
                AND wt.year = it.year
            LEFT JOIN ProgressLag pl 
                ON wt.student_key = pl.student_key 
                AND wt.course_key = pl.course_key
            LEFT JOIN SocialIsolation si 
                ON wt.student_key = si.student_key 
                AND wt.course_key = si.course_key
                AND wt.week_of_year = si.week_of_year
                AND wt.year = si.year;
        """
        db.execute_query(insert_query)
        print("Successfully loaded FactStudentRiskWeekly V2 with multi-factor risk calculation.")
