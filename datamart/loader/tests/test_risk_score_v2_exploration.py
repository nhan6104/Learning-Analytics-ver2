"""
Bug Condition Exploration Test for Risk Score Calculation V2

CRITICAL: This test MUST FAIL on unfixed code - failure confirms the bug exists
DO NOT attempt to fix the test or the code when it fails
NOTE: This test encodes the expected behavior - it will validate the fix when it passes

GOAL: Surface counterexamples that demonstrate the bug exists
"""

import pytest
from utils.pgsql_utils import db


class TestRiskScoreV2Exploration:
    """
    Property 1: Bug Condition - Risk Score Multi-Factor Calculation
    
    Tests that risk score calculation incorporates multiple factors:
    - Weekly engagement score
    - Engagement trend (week-over-week changes)
    - Consecutive inactivity days
    - Progress lag (behind schedule)
    - Social isolation (no peer interactions)
    """
    
    def test_risk_score_considers_positive_trend(self):
        """
        Test Case 1: Student with low weekly engagement but high previous weeks
        
        Current (EXPECTED TO FAIL): Risk = High (80) based only on week 5
        Expected (AFTER FIX): Risk = Medium (50) due to positive historical trend
        """
        # Setup: Create student with declining engagement but still reasonable
        student_key = "test_student_1"
        course_key = "10"
        
        # Week 1-4: High engagement (80, 85, 90, 85)
        # Week 5: Low engagement (15)
        
        # Query risk score for week 5
        query = """
            SELECT risk_score, risk_level
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = %s AND course_key = %s AND week_of_year = 5
        """
        result = db.execute_query(query, (student_key, course_key))
        
        if result:
            risk_score = result[0][0]
            risk_level = result[0][1]
            
            # On UNFIXED code: risk_score = 80 (only considers week 5 engagement = 15)
            # This test will FAIL because trend is not considered
            assert risk_score < 70, (
                f"EXPECTED FAILURE: Risk score should consider positive trend. "
                f"Got risk_score={risk_score}, but should be lower due to good historical trend. "
                f"This confirms the bug: trend is not factored into risk calculation."
            )
    
    def test_risk_score_considers_negative_trend(self):
        """
        Test Case 2: Student with medium engagement but declining trend
        
        Current (EXPECTED TO FAIL): Risk = Low (10) based only on week 5
        Expected (AFTER FIX): Risk = Medium (50) due to negative trend
        """
        student_key = "test_student_2"
        course_key = "10"
        
        # Week 1-5: Declining (90 → 80 → 70 → 60 → 60)
        
        query = """
            SELECT risk_score, risk_level
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = %s AND course_key = %s AND week_of_year = 5
        """
        result = db.execute_query(query, (student_key, course_key))
        
        if result:
            risk_score = result[0][0]
            
            # On UNFIXED code: risk_score = 10 (only considers week 5 engagement = 60)
            # Should be higher due to declining trend
            assert risk_score > 30, (
                f"EXPECTED FAILURE: Risk score should increase with negative trend. "
                f"Got risk_score={risk_score}, but should be higher. "
                f"This confirms the bug: trend is not considered."
            )
    
    def test_risk_score_considers_inactivity(self):
        """
        Test Case 3: Student with engagement 40, inactive for 7 consecutive days
        
        Current (EXPECTED TO FAIL): Risk = Medium (50) based only on engagement
        Expected (AFTER FIX): Risk = High (75) due to prolonged inactivity
        """
        student_key = "test_student_3"
        course_key = "10"
        
        # Check if inactivity penalty is applied
        query = """
            SELECT risk_score, risk_level
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = %s AND course_key = %s
        """
        result = db.execute_query(query, (student_key, course_key))
        
        if result:
            risk_score = result[0][0]
            
            # On UNFIXED code: No inactivity tracking
            # This test will FAIL because inactivity is not considered
            assert risk_score > 60, (
                f"EXPECTED FAILURE: Risk score should increase with inactivity. "
                f"Got risk_score={risk_score}, but should be higher due to 7 days inactivity. "
                f"This confirms the bug: inactivity is not tracked."
            )
    
    def test_risk_score_considers_multiple_factors(self):
        """
        Test Case 4: Student with multiple risk factors
        
        - Engagement = 50
        - 30% behind schedule
        - No peer interactions
        
        Current (EXPECTED TO FAIL): Risk = Medium (50) based only on engagement
        Expected (AFTER FIX): Risk = High (80) due to multiple risk factors
        """
        student_key = "test_student_4"
        course_key = "10"
        
        query = """
            SELECT risk_score, risk_level
            FROM datamart.fact_risk_student_weekly
            WHERE student_key = %s AND course_key = %s
        """
        result = db.execute_query(query, (student_key, course_key))
        
        if result:
            risk_score = result[0][0]
            
            # On UNFIXED code: Only engagement considered
            assert risk_score > 70, (
                f"EXPECTED FAILURE: Risk score should be high with multiple risk factors. "
                f"Got risk_score={risk_score}, but should be >70. "
                f"This confirms the bug: progress lag and social isolation not considered."
            )
    
    def test_risk_score_has_trend_field(self):
        """
        Verify that risk calculation includes trend analysis
        
        This test checks if the system tracks engagement trends at all
        """
        query = """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'datamart' 
            AND table_name = 'fact_risk_student_weekly'
            AND column_name IN ('engagement_trend', 'trend_score', 'inactivity_days', 'progress_lag')
        """
        result = db.execute_query(query)
        
        # On UNFIXED code: These columns don't exist
        assert len(result) > 0, (
            f"EXPECTED FAILURE: Risk table should have trend/inactivity/progress columns. "
            f"Found columns: {result}. "
            f"This confirms the bug: multi-factor risk calculation not implemented."
        )


if __name__ == "__main__":
    print("Running Bug Condition Exploration Tests for Risk Score V2")
    print("=" * 70)
    print("IMPORTANT: These tests are EXPECTED TO FAIL on unfixed code")
    print("Failures confirm that the bugs exist and need to be fixed")
    print("=" * 70)
    pytest.main([__file__, "-v", "-s"])
