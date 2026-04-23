import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()
from utils.kafka_utils.kafka import KafkaUtils
from utils.utils import build_time_window

class ingest_XAPI:
    def __init__(self):
        self.API_ENDPOINT = os.getenv("API_ENDPOINT_XAPI")   
        self.API_KEY = os.environ.get("API_KEY_XAPI") 
        self.API_SECRET = os.environ.get("API_SECRET_XAPI") 

        self.kafkautils = KafkaUtils()
        self.topic = os.getenv("KALFKA_TOPIC")
        self.API_KEY = os.getenv("API_KEY_SCORM")
        self.API_SECRET = os.getenv("API_SECRET_SCORM")
        self.API_ENDPOINT = os.getenv("API_BASE_ENDPOINT_SCORM")
    def get_statements(self, since, until,   limit = 100):

            producer = self.kafkautils.create_producer(bootstrapServers=os.getenv("BOOTSTRAPSERVERS"))
            headers = {
                "X-Experience-API-Version": "1.0.3"
            }
            params = {
                "limit": limit,
                "since": since,
                "until": until
            }
            try:
                
                url = "/lrs/IV2M3KSGCL/sandbox/xAPI/statements"
                while url:
                    endpoint =  self.API_ENDPOINT + url

                    response = requests.get(endpoint, headers=headers, params=params, auth=HTTPBasicAuth(self.API_KEY, self.API_SECRET))
                    print(json.dumps(response.json(), indent=4, ensure_ascii=False))

                    if response.status_code == 200:
                        for statement in response.json()['statements']:
                            producer.send(topic = self.topic , value = str(statement).encode('utf-8'))
                        
                    else:
                        print(f"Request failed with status code: {response.status_code}")

                    url = response.json()['more']
                    
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                raise str(e)
            
            finally:
                producer.close()
    
            
ingest = ingest_XAPI()
start_time = "2026-03-21 01:29:06"
duration = 60 * 60 * 8
since, until = build_time_window(start_time, duration)
print(since, until)
ingest.get_statements(since, until, limit= 5)

