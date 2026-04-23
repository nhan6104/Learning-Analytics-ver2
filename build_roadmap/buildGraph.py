from neo4j import GraphDatabase
import json

URI = "neo4j+s://3e4d8238.databases.neo4j.io"
AUTH = ("3e4d8238", "YtrF0uenKNKLAOJWSPHyCYlN3oKIcTDImPErRZWSZo0")


with GraphDatabase.driver(URI, auth=AUTH) as driver:
    driver.verify_connectivity()

def add_node(driver, label, properties):
    props_str = ", ".join(f"{key}: ${key}" for key in properties.keys())
    query = f"CREATE (n:{label} {{ {props_str} }}) RETURN n"
    driver.execute_query(query, **properties, database_="3e4d8238")


def add_edge(driver, from_label, from_props, to_label, to_props, edge_type, edge_props=None):
    # print(f"Adding edge: {from_label}({from_props}) -[{edge_type} {edge_props}]-> {to_label}({to_props})")
    from_props_str = " AND ".join(f"n.{key} = ${'from_' + key}" for key in from_props.keys())
    to_props_str = " AND ".join(f"m.{key} = ${'to_' + key}" for key in to_props.keys())
    
    edge_props_str = ", ".join(f"{key}: ${'edge_' + key}" for key in (edge_props or {}).keys())
    edge_props_str = f"{{ {edge_props_str} }}" if edge_props_str else ""
    
    query = (
        f"MATCH (n:{from_label}), (m:{to_label}) "
        f"WHERE {from_props_str} AND {to_props_str} "
        f"CREATE (n)-[r:{edge_type} {edge_props_str}]->(m) RETURN r"
    )
    
    params = {**{f"from_{k}": v for k, v in from_props.items()},
              **{f"to_{k}": v for k, v in to_props.items()},
              **{f"edge_{k}": v for k, v in (edge_props or {}).items()}}
        
    driver.execute_query(query, **params, database_="3e4d8238")


def buildLearningGraph():
    with open("learning_plan.json", "r") as f:
        learning_plan = json.load(f)

    Nodes = learning_plan.get("nodes", [])
    Edges = learning_plan.get("edges", [])

    with GraphDatabase.driver(URI, auth=AUTH) as driver:
        for node in Nodes:
            add_node(driver, node["id"], node)

        for edge in Edges:
            
            metadata = None
            if "confidence" in edge:
                metadata = {"confidence": edge.get("confidence", 0.0)}
                if "reason" in edge:
                    metadata["reason"] = edge.get("reason", "")

            add_edge(
                driver,
                edge["from"],
                {"id": edge["from"]},
                edge["to"],
                {"id": edge["to"]},
                edge["type"],
                metadata
            )
