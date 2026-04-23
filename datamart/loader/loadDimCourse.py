from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db

class LoadDimCourse:
    def __init__(self):
        self.datawarhouse_name = "datawarehouse"
        self.datamart_name = "datamart"
        self.moodle_db = moodle_db

    def load(self):
        query = """
            SELECT 
                c.id as course_key,
                c.fullname as course_name,
                'undergraduate' as course_level, -- Hardcoded or derived if possible
                (SELECT COUNT(*) FROM mdl_course_modules cm WHERE cm.course = c.id) as total_modules
            FROM mdl_course c
        """
        courses = self.moodle_db.inquiry_query(query)
        
        for course in courses:
            insert_query = f"""
                INSERT INTO {self.datamart_name}.dim_course (course_key, course_name, course_level, total_modules)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (course_key) DO UPDATE SET
                    course_name = EXCLUDED.course_name,
                    course_level = EXCLUDED.course_level,
                    total_modules = EXCLUDED.total_modules
            """
            db.execute_query(insert_query, (str(course['course_key']), course['course_name'], course['course_level'], course['total_modules']))