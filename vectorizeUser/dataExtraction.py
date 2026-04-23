from utils.pgsql_utils import PostgresDB
from vectorizeUser.cacl_utils import getMean, getQuantile, getSlope, getStd, getEntropyTransition, entropyNormalize, getTransitionRepeatRate
from datetime import datetime, timedelta
import pandas as pd


class extractTables:
    def __init__(self):
        self.db = PostgresDB(schema="datamart", dbname="test")

    def factStudentEngagementDaily(self, course_key, columns, window_size = 52):
        columns_temps = ", ".join(map(lambda col: f"eg.{col}", columns))
        FACT_STUDENT_ENGAGEMENT_DAILY = f"""
            WITH RankedData AS (
                SELECT 
                    {columns_temps},
                    dt.week,
                    eg.student_key,
                    eg.course_key,
                    ROW_NUMBER() OVER (PARTITION BY eg.student_key, dt.week ORDER BY dt.week DESC) as rn
                FROM datamart.fact_daily_student_engagement eg
                JOIN datamart.dim_time dt ON eg.date_key = dt.time_id
                WHERE course_key = %s
            )
            SELECT 
                *
            FROM RankedData
            WHERE rn <= {window_size}
        """

        columns_name, rows = self.db.execute_query(FACT_STUDENT_ENGAGEMENT_DAILY, (course_key,))
        return columns_name, rows

    def extractFactRiskStudent(self, course_key, columns, window_size = 52):
        columns_str = ", ".join(columns)
        FACT_RISK_STUDENT_WEEKLY = f"""
            WITH RankedData AS (
                SELECT 
                    {columns_str},
                    week_of_year,
                    student_key,
                    course_key,
                    ROW_NUMBER() OVER (PARTITION BY student_key ORDER BY week_of_year DESC) as rn
                FROM datamart.fact_risk_student_weekly
                WHERE course_key = %s
            )
            SELECT 
                *
            FROM RankedData
            WHERE rn <= {window_size}
            ORDER BY week_of_year DESC
        """


        columns_name, rows = self.db.execute_query(FACT_RISK_STUDENT_WEEKLY, (course_key,))
        return columns_name, rows

    def extractFactStudentEngagementDepth(self, course_key, columns):
        columns_str = ", ".join(columns)
        FACT_STUDENT_ENGAGEMENT_DEPTH_WEEKLY = f"""
            SELECT 
                {columns_str},
                student_key,
                course_key,
                resource_key
            FROM datamart.fact_student_engagement_depth
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(FACT_STUDENT_ENGAGEMENT_DEPTH_WEEKLY, (course_key,))
        df = pd.DataFrame(rows, columns=columns_name)

        return columns_name, rows   

    def extractFactStudentCourseLifeCycle(self, course_key, columns):
        columns_str = ", ".join(columns)
        FACT_STUDENT_COURSE_LIFECYCLE = f"""
            SELECT 
                {columns_str},
                student_key,
                course_key
            FROM datamart.fact_student_course_lifecycle
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(FACT_STUDENT_COURSE_LIFECYCLE, (course_key,))
        return columns_name, rows   

    def extractFactStudentDeadlineProximity(self, course_key, columns):
        columns_str = ", ".join(columns)
        FACT_STUDENT_DEADLINE_PROXIMITY = f"""
            SELECT 
                {columns_str},
                student_key,
                course_key,
                resource_key
            FROM datamart.fact_student_deadline_proximity
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(FACT_STUDENT_DEADLINE_PROXIMITY, (course_key,))
        return columns_name, rows

   
    def extractFactStudentTimeAffinity (self, course_key, columns):
        columns_str = ", ".join(columns)
        FACT_STUDENT_TIME_AFFINITY = f"""
            SELECT 
                {columns_str},
                student_key,
                course_key
            FROM datamart.fact_student_time_affinity
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(FACT_STUDENT_TIME_AFFINITY, (course_key,))
        return columns_name, rows
    
    def extractCourse(self, course_key, columns):
        columns_str = ", ".join(columns)
        COURSE_QUERY = f"""
            SELECT
                {columns_str},
                course_key
            FROM datamart.dim_resource
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(COURSE_QUERY, (course_key,))
        return columns_name, rows
    
    def extractTransitionActivity(self, course_key, columns):
        columns_str = ", ".join(columns)
        TRANSITION_ACTIVITY_QUERY = f"""
            SELECT
                {columns_str},
                student_key,
                course_key
            FROM datamart.fact_activity_transitions_detail
            WHERE course_key = %s
        """

        columns_name, rows = self.db.execute_query(TRANSITION_ACTIVITY_QUERY, (course_key,))
        return columns_name, rows


class extractIndex:
    def __init__(self):
        self.tables = extractTables()

    def getStudentEngagementIndex(self, course_key):
        columns = ["engagement_score"]
        columns_name, rows = self.tables.factStudentEngagementDaily(course_key, columns)

        df = pd.DataFrame(rows, columns=columns_name)

        engagement_index = df.groupby("student_key")["engagement_score"].agg(
           engagement_mean = lambda x: getMean(x),
           engagement_Q1 = lambda x: getQuantile(x, 0.25),
           engagement_Q3 = lambda x: getQuantile(x, 0.75),
           engagement_slope = lambda x: getSlope(x)     
        )
        return engagement_index

    def getRiskIndex(self, course_key):
        columns = ["risk_score"]
        columns_name, rows = self.tables.extractFactRiskStudent(course_key, columns)
        
        df = pd.DataFrame(rows, columns=columns_name)

        risk_index = df.groupby("student_key")["risk_score"].agg(
            risk_mean = lambda x: getMean(x),
            risk_slope = lambda x: getSlope(x),
            risk_Q1 = lambda x: getQuantile(x, 0.25),
            risk_Q3 = lambda x: getQuantile(x, 0.75)
        )
        return risk_index
    

    def getStudentEngagementDepthIndex(self, course_key):
        columns = ["depth_ratio"]
        columns_name, rows = self.tables.extractFactStudentEngagementDepth(course_key, columns)

        df = pd.DataFrame(rows, columns=columns_name)
        engagement_depth_index = df.groupby(["student_key", "resource_key"])["depth_ratio"].agg(
            depth_ratio_mean = lambda x: getMean(x),
            depth_ratio_std = lambda x: getStd(x),
            depth_ratio_Q1 = lambda x: getQuantile(x, 0.25),
            depth_ratio_Q3 = lambda x: getQuantile(x, 0.75)
        )
        return engagement_depth_index
        
    
    def getProgressIndex(self, course_key):
        progress_columns = ["milestone_25_date", "milestone_50_date", "milestone_75_date"]
        progress_columns_name, progress_rows = self.tables.extractFactStudentCourseLifeCycle(course_key, progress_columns)

        # completion_columns = ["is_completed"]
        # completion_columns_name, completion_rows = self.tables.extractFactStudentDeadlineProximity(course_key, completion_columns)


        df = pd.DataFrame(progress_rows, columns=progress_columns_name)
        return df
    
    def getCourseStructure(self, course_key):
        columns = ["section_key", "resource_key"]
        columns_name, rows = self.tables.extractCourse(course_key, columns)
        df = pd.DataFrame(rows, columns=columns_name)

        course_structure = df.groupby("section_key")["resource_key"].agg(
            resource_count = lambda x: len(x.unique()),
            resource_keys = lambda x: list(x.unique()),
        )

        return course_structure
    
    
    
    def getActivityTransitions(self, course_key):

        course_structure = self.getCourseStructure(course_key)

        resource_to_section = {}

        for section_key, row in course_structure.iterrows():
            for resource_key in row["resource_keys"]:
                resource_to_section[resource_key] = section_key
             
        columns = ["from_resource_key", "to_resource_key", "transition_count"]
        columns_name, rows = self.tables.extractTransitionActivity(course_key, columns)

        df = pd.DataFrame(rows, columns=columns_name)

        df["from_section_key"] = df["from_resource_key"].map(resource_to_section)
        df["to_section_key"] = df["to_resource_key"].map(resource_to_section)
        df["same_section"] = df["from_section_key"] == df["to_section_key"]
        activity_transitions_index = df[df["same_section"] ==  True].groupby(["student_key", "from_section_key", "to_section_key"]).apply(
            lambda x: pd.Series({
                "transition": list((zip(zip(x["from_resource_key"], x["to_resource_key"]), x["transition_count"])))
            })
        )
        return activity_transitions_index

    def getActivityTransitionsIndex(self, course_key):
        activity_transitions = self.getActivityTransitions(course_key)
        activity_transitions_index = activity_transitions.groupby(["student_key", "from_section_key", "to_section_key"])["transition"].agg(
            transition_entropy = lambda x: entropyNormalize(getEntropyTransition(x.iloc[0]), len(x.iloc[0])),
            transition_repeat_rate = lambda x: getTransitionRepeatRate(x.iloc[0])
        )

        return activity_transitions_index

if __name__ == "__main__":
    extractor = extractIndex()
    course_key = "101"
    # engagement_index = extractor.getStudentEngagementIndex(course_key)
    # risk_index = extractor.getRiskIndex(course_key)
    # engagement_depth_index = extractor.getStudentEngagementDepthIndex(course_key)
    # progress_index = extractor.getProgressIndex(course_key)
    # course_structure = extractor.getCourseStructure(course_key)
    # activity_transitions = extractor.getActivityTransitions(course_key)
    activity_transitions_index = extractor.getActivityTransitionsIndex(course_key)


    print(activity_transitions_index)