import os
import json
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()
from utils.kafka_utils.kafka import KafkaUtils

class ingest_XAPI:
    def __init__(self):
        self.API_ENDPOINT = os.getenv("API_ENDPOINT_XAPI")   
        self.API_KEY = os.environ.get("API_KEY_XAPI") 
        self.API_SECRET = os.environ.get("API_SECRET_XAPI") 

        self.kafkautils = KafkaUtils()
        self.topic = os.getenv("KALFKA_TOPIC")

    def get_statements(self, limit = 100):

            producer = self.kafkautils.create_producer(bootstrapServers=os.getenv("BOOTSTRAPSERVERS"))
            headers = {
                "X-Experience-API-Version": "1.0.3"
            }
            params = {
                "limit": limit
            }
            try:
                response = requests.get(self.API_ENDPOINT, headers=headers, params=params, auth=HTTPBasicAuth(self.API_KEY, self.API_SECRET))
                print(json.dumps(response.json(), indent=4, ensure_ascii=False))
                
                if response.status_code == 200:
                    for response in response.json()['statements']:
                        producer.send(topic = self.topic , value = str(response).encode('utf-8'))
                    
                    producer.close()
                else:
                    print(f"Request failed with status code: {response.status_code}")

            except Exception as e:
                print(f"An error occurred: {str(e)}")
                raise str(e)