from typing import TypedDict, Annotated, List, Literal
from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.message import add_messages
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langgraph.types import interrupt, Command
from promptTemplate import  EXTRACT_LEARNING_PLAN
from build_roadmap.utils import extract_json
import requests
import json
import re
import os




class Query(TypedDict):
    number_of_scene: int
    queries:  List[str]

class MessageState(TypedDict):
    original_query: str
    enriched_query: List[Query]
    result: any
    top_k_task3: List[int]
    top_k_task3_index: int
    search_input: Query
    mode: int

class Agent:
    def __init__(self):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            google_api_key='AIzaSyAkyF3QedUqasvKOBQMDf7XqZEoPxDuIv4'
        )


    def generate_learning_plan(self, resource_list_json):
        extract_learning_chain_plan = EXTRACT_LEARNING_PLAN | self.llm

        learning_msg = extract_learning_chain_plan.invoke({
            "YOUR_RESOURCE_LIST_JSON": resource_list_json
        })


        cleaned_plan = extract_json(learning_msg.content)
        return cleaned_plan
    


# with open("course_structure.json", "r") as f:
#     text = json.load(f)


# extract_learning_chain_plan = EXTRACT_LEARNING_PLAN | llm

# learning_msg = extract_learning_chain_plan.invoke({
    
#     "YOUR_RESOURCE_LIST_JSON": text
# })



# # fallback: try direct
# cleaned_plan = extract_json(learning_msg.content)
# print(cleaned_plan)
# with open("learning_plan.json", "w") as f:
#     json.dump(cleaned_plan, f, indent=4)
