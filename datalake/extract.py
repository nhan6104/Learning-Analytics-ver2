import os
import json
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()

from utils.kafka_utils.kafka import KafkaUtils

class DataExtractor:
    def __init__(self):
        self.API_ENDPOINT = os.getenv("API_ENDPOINT_SCORM")           # Trả về None nếu biến không tồn tại
        self.API_KEY = os.environ.get("API_KEY_SCORM") 
        self.API_SECRET = os.environ.get("API_SECRET_SCORM") 

        kafkaClient = KafkaUtils()
        self.consumer = kafkaClient.create_consumer(bootstrapServers=os.getenv("BOOTSTRAPSERVERS"), topic='xapi_statements')
    
    def extractData(self):
        all_records = []
    
        while True:
            records = self.consumer.poll(timeout_ms=1000)
            
            if not records:
                break
        
            for tp, msgs in records.items():
                print(tp)
                all_records.extend(msgs)

        print(type(all_records[0]))
        return all_records
    
