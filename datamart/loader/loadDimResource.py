from utils.moodle_db_utils import moodle_db
from utils.pgsql_utils import db

class LoadDimResource:
    def __init__(self):
        self.datawarhouse_name = "datawarehouse"
        self.datamart_name = "datamart"
        self.moodle_db = moodle_db

    def load(self):
        query = """
            SELECT 
                cm.id as resource_key,
                m.name as resource_type,
                CASE 
                    WHEN m.name = 'resource' THEN (SELECT name FROM mdl_resource WHERE id = cm.instance)
                    WHEN m.name = 'quiz' THEN (SELECT name FROM mdl_quiz WHERE id = cm.instance)
                    WHEN m.name = 'assign' THEN (SELECT name FROM mdl_assign WHERE id = cm.instance)
                    WHEN m.name = 'forum' THEN (SELECT name FROM mdl_forum WHERE id = cm.instance)
                    WHEN m.name = 'page' THEN (SELECT name FROM mdl_page WHERE id = cm.instance)
                    WHEN m.name = 'url' THEN (SELECT name FROM mdl_url WHERE id = cm.instance)
                    WHEN m.name = 'book' THEN (SELECT name FROM mdl_book WHERE id = cm.instance)
                    WHEN m.name = 'folder' THEN (SELECT name FROM mdl_folder WHERE id = cm.instance)
                    WHEN m.name = 'label' THEN (SELECT name FROM mdl_label WHERE id = cm.instance)
                    WHEN m.name = 'feedback' THEN (SELECT name FROM mdl_feedback WHERE id = cm.instance)
                    ELSE m.name
                END as resource_name,
                cm.course as course_key,
                cs.id as section_id
            FROM mdl_course_modules cm
            JOIN mdl_modules m ON cm.module = m.id
            JOIN mdl_course_sections cs ON cm.section = cs.id
        """
        resources = self.moodle_db.inquiry_query(query)
        
        for res in resources:
            insert_query = f"""
                INSERT INTO {self.datamart_name}.dim_resource (resource_key, resource_name, resource_type, section_key, course_key)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (resource_key) DO UPDATE SET
                    resource_name = EXCLUDED.resource_name,
                    resource_type = EXCLUDED.resource_type,
                    section_key = EXCLUDED.section_key,
                    course_key = EXCLUDED.course_key
            """
            db.execute_query(insert_query, (str(res['resource_key']), res['resource_name'], res['resource_type'], str(res['section_id']), str(res['course_key'])))
    