import xml.etree.ElementTree as ET
import json


def parse_moodle_backup(xml_string: str):
    root = ET.fromstring(xml_string)

    info = root.find("information")
    contents = info.find("contents")
    
    # ===== 1. Extract course info =====
    course = contents.find("course")
    course_id = course.find("courseid").text
    course_title = course.find("title").text

    # ===== 2. Build section map =====
    section_map = {}
    sections = contents.find("sections").findall("section")

    for sec in sections:
        section_id = sec.find("sectionid").text
        title = sec.find("title").text

        section_map[section_id] = {
            "title": title
        }

    # ===== 3. Attach activities =====
    activities = contents.find("activities").findall("activity")

    for act in activities:
        section_id = act.find("sectionid").text
        module_id = act.find("moduleid").text

        resource = {
            "resource_type": act.find("modulename").text,
            "resource_dir": act.find("directory").text,
            "resource_name": act.find("title").text
        }

        # ensure section exists
        if section_id not in section_map:
            section_map[section_id] = {"title": None}

        section_map[section_id][module_id] = resource

    # ===== 4. Final structure =====
    result = {
        "course_id": course_id,
        "course_title": course_title,
        "course_structure": section_map
    }

    return result


# ===== Usage =====
if __name__ == "__main__":
    with open("backup-course-6-20260315-1329/moodle_backup.xml", "r", encoding="utf-8") as f:
        xml_data = f.read()

    parsed = parse_moodle_backup(xml_data)
    with open("temp.json", "w", encoding="utf-8") as f:
        json.dump(parsed, f, indent=2, ensure_ascii=False)
        print(json.dumps(parsed, indent=2, ensure_ascii=False))