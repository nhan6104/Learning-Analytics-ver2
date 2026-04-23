import json
from build_roadmap.agent import Agent

def build_course_structure_module_level(course_structure_path):
    with open(course_structure_path, "r") as f:
        course_data = json.load(f)

    relationship_plan_list = list()
    
    nodes = []

    sectionList = list(course_data.keys())
    for section in sectionList:
        nodes.append({
            "id": section,
            "title": course_data[section]["title"]
        })
        modules = [k for k in course_data[section].keys() if k != "title"]
        for module in modules:
            nodes.append({
                "id": module,
                "title": course_data[section][module]["title"]
            })
            resourceList = list(course_data[section][module].keys())
            resourceList.remove("title") 
            relationship_plan_list.append((section, module, "HAS_MODULE"))   
            for resource in resourceList:
                relationship_plan_list.append((module, resource, "HAS_RESOURCE"))

    edge = []
    for relationship in relationship_plan_list:
        edge.append({
            "from": relationship[0],
            "to": relationship[1],
            "type": relationship[2]
        })
        print(f"{relationship[0]} {relationship[2]} {relationship[1]}")

    relationship = {
        "nodes": nodes,
        "edges": edge
    }

    return relationship 


def build_course_structure_resource_level(course_structure_path):
    agent = Agent()

    with open(course_structure_path, "r") as f:
        resource_list_json = json.load(f)

    relationship = agent.generate_learning_plan(resource_list_json)
    return relationship


def combine_relationships(module_level_relationship, resource_level_relationship):
    combined_relationship = {
        "nodes": module_level_relationship["nodes"] + resource_level_relationship["nodes"],
        "edges": module_level_relationship["edges"] + resource_level_relationship["edges"]
    }

    with open("learning_graph.json", "w") as f:
        json.dump(combined_relationship, f, indent=4)
