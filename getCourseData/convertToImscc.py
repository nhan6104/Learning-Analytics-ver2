import zipfile
import os
import shutil
import xml.etree.cElementTree as ET
from datetime import datetime
import tarfile
import json
import html
from html import escape
import re 


WORK_DIR = "mbz_extract"
OUTPUT_DIR = "imscc_build"
os.makedirs(OUTPUT_DIR, exist_ok=True)

with open("./temp.json", "r") as f:
    data = json.load(f)


def unzip_mbz(mbz_path):

    if os.path.exists(WORK_DIR):
        shutil.rmtree(WORK_DIR)

    os.makedirs(WORK_DIR, exist_ok=True)

    # đổi tên mbz -> zip
    zip_path = mbz_path.replace(".mbz", ".tar.gz")

    os.rename(mbz_path, zip_path)

    # unzip
    with tarfile.open(zip_path, "r:gz") as tar:
        tar.extractall(WORK_DIR)

    print("MBZ renamed to ZIP and extracted")


# unzip_mbz("./backup-moodle2-course-7-applied_english-20260311-1345.mbz")

NS = {
    "def": "http://www.imsglobal.org/xsd/imsccv1p3/imscp_v1p1",
    "lomimscc": "http://ltsc.ieee.org/xsd/imsccv1p3/LOM/manifest",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance"
}


def tag(ns, name):
    return f"{{{NS[ns]}}}{name}"


def build_imsmanifest():
    manifest = ET.Element(
        tag("def", "manifest"),
        {
            "identifier": "MANIFEST1",
            tag("xsi", "schemaLocation"): (
                f"{NS['def']} "
                "http://www.imsglobal.org/profile/cc/ccv1p3/ccv1p3_imscp_v1p2_v1p0.xsd"
            )
        }
    )

    # metadata
    metadata = ET.SubElement(manifest, tag("def", "metadata"))
    ET.SubElement(metadata, tag("def", "schema")).text = "IMS Common Cartridge"
    ET.SubElement(metadata, tag("def", "schemaversion")).text = "1.3.0"

    # lom metadata
    lom = ET.SubElement(metadata, tag("lomimscc", "lom"))
    general = ET.SubElement(lom, tag("lomimscc", "general"))

    ET.SubElement(
        ET.SubElement(general, tag("lomimscc", "title")),
        tag("lomimscc", "string")
    ).text = "Loaded Course"

    ET.SubElement(general, tag("lomimscc", "language")).text = "en"


    return manifest

def convert_to_organization():
    organizations = ET.Element("organizations")

    organization = ET.SubElement(organizations, "organization")
    organization.set("identifier", "org_1")
    organization.set("structure", "rooted-hierarchy")

    item = ET.SubElement(organization, "item")
    item.set("identifier", "LearningModules")


    course_structure = data["course_structure"]

    for sec_id, modules in course_structure.items():
        section = ET.SubElement(item, "item")
        section.set("identifier", f"section_{sec_id}")
        section_title = ET.SubElement(section, "title")
        section_title.text = course_structure[sec_id]["title"]

        for module_id, el in modules.items():
            if module_id == "title":
                continue

            module = ET.SubElement(section, "item")
            module.set("identifier", f"module_{module_id}" )
            module.set("identifierref", modules[module_id]["resource_dir"].split('/')[1])

            sec_title = ET.SubElement(module, "title")
            sec_title.text = el["resource_name"]

    return organizations

def clean_html(raw_html):
    """Remove inline styles, empty spans, and messy Moodle HTML"""
    if not raw_html:
        return ""

    # remove style=""
    raw_html = re.sub(r'style="[^"]*"', '', raw_html)

    # remove class=""
    raw_html = re.sub(r'class="[^"]*"', '', raw_html)

    # remove empty spans
    raw_html = re.sub(r'<span>\s*</span>', '', raw_html)

    # remove redundant nested spans
    raw_html = re.sub(r'</?span>', '', raw_html)

    # fix multiple <br>
    raw_html = re.sub(r'(<br\s*/?>\s*){2,}', '<br/>', raw_html)

    return raw_html.strip()

def convert_page(filePath):
    tree = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/page.xml")
    root = tree.getroot()

    module_id = root.attrib.get("moduleid", "unknown")

    page = root.find("page")

    title = page.findtext("name", default="Untitled")
    intro = page.findtext("intro", default="")
    content = page.findtext("content", default="")

    # decode HTML entities
    intro_html = html.unescape(intro)
    content_html = html.unescape(content)

    # clean HTML
    intro_html = clean_html(intro_html)
    content_html = clean_html(content_html)

    # combine
    body = f"""
    <div>
        <div class="title">{title}</div>
        <div class="introduction">{intro_html}</div>
        <div class="content">{content_html}</div>
    </div>
    """

    # wrap full HTML
    final_html = f"""<!DOCTYPE html>
    <html>
        <body>
            <div class="page">
                {body}
            </div>
        </body>
    </html>
    """

    return final_html

def convert_url(filePath):

    tree = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/url.xml")
    root = tree.getroot()
    
    title = root.find(".//name").text
    url = root.find(".//externalurl").text

    # generate HTML
    html = f"""<!DOCTYPE html>
                <html>
                    <body>
                        <div class="url">
                            <div class="title">{title}</div>
                            <div class="link"><a href="{url}">{url}</a></div>
                        </div>
                    </body>
                </html>
            """

    return html

def convert_assign(filePath):    
        root = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/assign.xml")
        assign = root.find(".//assign")

        # ===== Extract =====
        title = assign.findtext("name")

        intro_raw = assign.findtext("intro")
        content_html = html.unescape(intro_raw or "")

        grade = assign.findtext("grade")
        grade = int(grade) if grade else 0

        # ===== Detect submission types =====
        submission_types = []

        for pc in assign.findall(".//plugin_config"):
            plugin = pc.findtext("plugin")
            name = pc.findtext("name")
            value = pc.findtext("value")

            if plugin == "file" and name == "enabled" and value == "1":
                submission_types.append("online_upload")

            if plugin == "onlinetext" and value == "1":
                submission_types.append("online_text_entry")

        if not submission_types:
            submission_types = ["none"]

        # ===== Build IMSCC XML =====
        ns = "http://www.imsglobal.org/xsd/imscc_extensions/assignment"
        ET.register_namespace("", ns)

        assignment = ET.Element(
            "assignment",
            {
                "xmlns": ns,
                "identifier": "generated_id"
            }
        )

        title_el = ET.SubElement(assignment, "title")
        title_el.text = title

        text_el = ET.SubElement(assignment, "text", {"texttype": "text/html"})
        text_el.text = content_html

        gradable_el = ET.SubElement(
            assignment,
            "gradable",
            {"points_possible": str(grade)}
        )
        gradable_el.text = "true" if grade > 0 else "false"

        submission_el = ET.SubElement(assignment, "submission_formats")
        submission_el.text = ",".join(submission_types)

        return assignment

def convert_resource(filePath):
    tree = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/resource.xml")
    activity = tree.getroot()
    
    context_id = activity.attrib.get("contextid")

    resource =  activity.find(".//resource")
    resource_name = resource.findtext("name") 
    resource_intro = resource.findtext("intro")

    resource_tree = ET.parse(f"./backup-course-6-20260315-1329/files.xml")
    root = resource_tree.getroot()

    files = root.findall(".//file")
    for file in files:
        contextId = file.findtext("contextid", "")
        if str(context_id) == contextId and int(file.findtext("filesize", "")) > 0:

            filename = file.findtext("filename", "").split('.')[0]
            file_type = file.findtext("mimetype", "")
            author = file.findtext("author", "")

            return f"""<!DOCTYPE html>
            <html>
                <body>
                    <div class="resource">
                        <div class="name">{resource_name}</div>
                        <div class="introduction">{resource_intro}</div>
                        <div class="filename">{filename}</div>
                        <div class="filetype">{file_type}</div>
                        <div class="author">{author}</div>
                    </div>
                </body>
            </html>
            """

def convert_folder(filePath):
    tree = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/folder.xml")
    activity = tree.getroot()

    context_id = activity.attrib.get("contextid")

    folder =  activity.find(".//folder")
    folder_name = folder.findtext("name") 
    folder_intro = folder.findtext("intro")

    tree = ET.parse(f"./backup-course-6-20260315-1329/files.xml")
    root = tree.getroot()

    files = root.findall(".//file")
    folder_path = None
    fileList = ""
    for file in files:
        contextId = file.findtext("contextid", "")
        if str(context_id) == contextId and int(file.findtext("filesize", "")) > 0:
            folder_path = file.findtext("filepath", "").strip("/")
            filename = file.findtext("filename", "").split(".")[0]
            file_type = file.findtext("mimetype", "")
            author = file.findtext("author", "")

            fileList +=  f""" <div class="file">
                            <div class="filename">{filename}</div>
                            <div class="filetype">{file_type}</div>
                            <div class="author">{author}</div>
                        </div>
                    """

    html = f"""<!DOCTYPE html>
                <html>
                    <body>
                        <div class="folder">
                            <div class="name">{folder_name}</div>
                            <div class="introduction">{folder_intro}</div>
                            <div class="path">{folder_path}</div>
                            {fileList}
                        </div>
                    </body>
                </html>
            """

    return html

def convert_forum(filePath):
    tree = ET.parse(f"./backup-course-6-20260315-1329/{filePath}/forum.xml")
    root = tree.getroot()
    
    forum = root.find(".//forum")

    forum_name = forum.findtext("name")
    forum_type = forum.findtext("type")
    forum_intro = forum.findtext("intro")

    # generate HTML
    html = f"""<!DOCTYPE html>
                <html>
                    <body>
                        <div class="forum">
                            <div class="type">{forum_type}</div>
                            <div class="name">{forum_name}</div>
                            <div class="intro">{forum_intro}</div>
                        </div>
                    </body>
                </html>
            """

    return html

def normalize_resource(module):
    resource_type = module["resource_type"]
    resource_dir = module["resource_dir"]
    file_ref = None
    if resource_type == "url": 
        url_html = convert_url(resource_dir)
        file_ref = f"{resource_dir.split('/')[1]}.html"
        with open(f"{OUTPUT_DIR}/{file_ref}", "w", encoding="utf-8") as f:
            f.write(url_html)

    elif resource_type == "page":
        page_html = convert_page(resource_dir)
        file_ref = f"{resource_dir.split('/')[1]}.html"
        with open(f"{OUTPUT_DIR}/{file_ref}", "w", encoding="utf-8") as f:
            f.write(page_html)
    
    elif resource_type == "assign":
        assign_xml = convert_assign(resource_dir)
        assign_tree = ET.ElementTree(assign_xml)
        file_ref = f"{resource_dir.split('/')[1]}.xml"
        assign_tree.write(f"{OUTPUT_DIR}/{file_ref}", encoding="utf-8", xml_declaration=True)

    elif resource_type == "folder":
        folder_html = convert_folder(resource_dir)
        file_ref = f"{resource_dir.split('/')[1]}.html"
        with open(f"{OUTPUT_DIR}/{file_ref}", "w", encoding="utf-8") as f:
            f.write(folder_html)
            
    elif resource_type == "resource":
        resource_html = convert_resource(resource_dir)
        file_ref = f"{resource_dir.split('/')[1]}.html"
        with open(f"{OUTPUT_DIR}/{file_ref}", "w", encoding="utf-8") as f:
            f.write(resource_html)
    
    elif resource_type == "forum":
        forum_html = convert_forum(resource_dir)
        file_ref = f"{resource_dir.split('/')[1]}.html"
        with open(f"{OUTPUT_DIR}/{file_ref}", "w", encoding="utf-8") as f:
            f.write(forum_html)

    return file_ref

def convert_to_resource ():
    course_structure = data["course_structure"]

    resources = ET.Element("resources")

    RESOURCETYPE = dict({
        "url": "webcontent",
        "page": "webcontent",
        "forum": "imsdt_xmlv1p3",
        "assign": "assignment_xmlv1p0",
        "resource": "webcontent",
        "folder": "webcontent",
        "quiz": "imsqti_xmlv1p2/imscc_xmlv1p3/assessment"
    })

    for sec_id, modules in course_structure.items():
        for module_id, el in modules.items():
            if module_id == "title":
                continue
            
            file_ref = normalize_resource(modules[module_id])
            resource = ET.SubElement(resources, "resource")
            resource.set("identifier", modules[module_id]["resource_dir"].split('/')[1])
            resource.set("href", file_ref)
            resource.set("type", RESOURCETYPE[modules[module_id]["resource_type"]])

            file = ET.SubElement(resource, "file")
            # file_ref = modules[module_id]["resource_dir"] + '/' + modules[module_id]["resource_type"] + '.xml'
            file.set("href",  file_ref)

    return resources


def build_imscc(mbz_path):
    unzip_mbz(mbz_path)
    mainfest = build_imsmanifest()
    organizations = convert_to_organization()
    resources = convert_to_resource()

    mainfest.append(organizations)
    mainfest.append(resources)

    # register namespace
    ET.register_namespace("", NS["def"])
    ET.register_namespace("lomimscc", NS["lomimscc"])
    ET.register_namespace("xsi", NS["xsi"])

    
    xml_tree = ET.ElementTree(mainfest)
    xml_tree.write(f"{OUTPUT_DIR}/imsmanifest.xml", encoding="utf-8", xml_declaration=True)   
    print(mainfest)

# if __name__ == "__main__":

#     # folder_html = convert_folder(73)
#     # print(folder_html)
#     # with open(f"folder_73.html", "w", encoding="utf-8") as f:
#     #     f.write(folder_html)

#     # resource_html = convert_resource(74)
#     # print(resource_html)


#     # page_file = "page_33"
#     # url_html = convert_page(page_file)
#     # print(url_html)
#     # with open(f"{page_file}.html", "w", encoding="utf-8") as f:
#     #     f.write(url_html)

#     # url_file = "url_74"
#     # _, url_html = convert_url(url_file)
#     # print(url_html)
#     # with open(f"{url_file}.html", "w", encoding="utf-8") as f:
#     #     f.write(url_html)


#     # assign_file = "assign_53"
#     # assign = convert_assign(assign_file)

#     # assign_tree = ET.ElementTree(assign)
#     # assign_tree.write("assign_53.xml", encoding="utf-8", xml_declaration=True)

#     mainfest = build_imsmanifest()
#     organizations = convert_to_organization()
#     resources = convert_to_resource()

#     mainfest.append(organizations)
#     mainfest.append(resources)

#         # register namespace
#     ET.register_namespace("", NS["def"])
#     ET.register_namespace("lomimscc", NS["lomimscc"])
#     ET.register_namespace("xsi", NS["xsi"])

    
#     xml_tree = ET.ElementTree(mainfest)
#     xml_tree.write(f"{OUTPUT_DIR}/imsmanifest.xml", encoding="utf-8", xml_declaration=True)   
#     print(mainfest)