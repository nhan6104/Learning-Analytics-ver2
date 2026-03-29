from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db

class LoadDimSection:
    def __init__(self):
        self.dm = "datamart"
        self.moodle_db = moodle_db

    def load(self):
        query = "SELECT id, course, name, section FROM mdl_course_sections"
        sections = self.moodle_db.inquiry_query(query)
        
        for s in sections:
            insert_query = f"""
                INSERT INTO {self.dm}.dim_section (section_key, section_name, section_number, course_key)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (section_key) DO UPDATE SET
                    section_name = EXCLUDED.section_name,
                    section_number = EXCLUDED.section_number,
                    course_key = EXCLUDED.course_key
            """
            # Nếu name trống, dùng Section + số thứ tự
            name = s['name'] if s['name'] else f"Section {s['section']}"
            db.execute_query(insert_query, (str(s['id']), name, s['section'], str(s['course'])))
        print("Successfully loaded DimSection.")
