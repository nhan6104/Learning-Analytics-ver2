import xml.etree.ElementTree as ET
import json
from bs4 import BeautifulSoup



def parse_webcontent(file_path):
    content = {}
    with open(file_path, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "html.parser")
        
    type_div = soup.find("div")  # div đầu tiên
    type_resource = type_div.get("class")[0]  # trả về list

    print(type_resource)
    if type_resource == "url":
        title_el = soup.find("div", class_="title").text.strip()
        content = {
            "title": title_el
        }

    elif type_resource == "page":
        title = soup.find("div", class_="title").text.strip()
        intro = soup.find("div", class_="introduction").text.strip()
        content_div = soup.find("div", class_="content")
        content = content_div.get_text(separator="\n", strip=True)

        content = {
            "title": title,
            "introduction": intro,
            "content": content
        }

    elif type_resource == "resource":
        name = soup.find("div", class_="name").text.strip()
        introduction = soup.find("div", class_="introduction").text.strip()
        fileType = soup.find("div", class_="filetype").text.strip()
        author = soup.find("div", class_="author").text.strip()

        content = {
            "title": name,
            "introduction": introduction,
            "fileType": fileType,
            "author": author
        }

    elif type_resource == "folder":
        folder = soup.find("div", class_="folder")

        # metadata
        name = folder.find("div", class_="name").get_text(strip=True)

        intro_el = folder.find("div", class_="introduction")
        introduction = intro_el.get_text(" ", strip=True) if intro_el else None

        path_el = folder.find("div", class_="path")
        path = path_el.get_text(strip=True) if path_el else None

        # files
        files = []
        for file_div in folder.find_all("div", class_="file"):
            filename = file_div.find("div", class_="filename").get_text(strip=True)
            filetype = file_div.find("div", class_="filetype").get_text(strip=True)
            author = file_div.find("div", class_="author").get_text(strip=True)

            files.append({
                "filename": filename,
                "filetype": filetype,
                "author": author
            })

        content = {
            "type": "folder",
            "name": name,
            "introduction": introduction,
            "path": path,
            "files": files
        }


    return content

def mapCourseToJson(imscc_file_path):

    BASE_DIR  = imscc_file_path

    course_root = ET.parse(f'{BASE_DIR}/imsmanifest.xml').getroot()
    
    ns = {
        "ns": "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1"
    }

    # lấy organization
    org = course_root.find(".//ns:organization", ns)

    # level 1: LearningModules
    learning_modules = org.find("ns:item", ns)

    # level 2: sections
    sections = learning_modules.findall("ns:item", ns)

    course_structure = {}


    resource_details = {}

    resources = course_root.findall(f".//ns:resource", ns)
    for resource in resources:
        resource_id = resource.get("identifier")
        resource_type = resource.get("type")
        file_name = resource.find(".//ns:file", ns).get("href")

        if resource_type == "webcontent":
            content = parse_webcontent(f"{BASE_DIR}/{file_name}")
            resource_details[resource_id] = content



    for section in sections:
        section_title_el = section.find("ns:title", ns)
        section_title = section_title_el.text if section_title_el is not None else None
        section_id = section.get("identifier")
        
        course_structure[section_id] = {
            "title": section_title
        }
        print(f"\nSECTION: {section_title}")

        # level 3: modules
        modules = section.findall("ns:item", ns)
        module_list = []
        for module in modules:
            module_title_el = module.find("ns:title", ns)
            module_title = module_title_el.text if module_title_el is not None else None
            module_key = module.get("identifier")
            resource_ref = module.get("identifierref")
            
            module_info = {
                "title": module_title,
                resource_ref: resource_details.get(resource_ref, {})
            }
            course_structure[section_id][module_key] = module_info
        
    return course_structure


if __name__ == "__main__":
    BASE_DIR = "imscc_build"
    course_structure = mapCourseToJson(f"{BASE_DIR}/imsmanifest.xml")


    # content = parse_webcontent(f"{BASE_DIR}/url_89.html")



    print(course_structure)

    with open("course_structure.json", "w") as f:
        json.dump(course_structure, f, indent=2)
