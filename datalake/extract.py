import os
import json
import pandas as pd
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
load_dotenv()

from utils.kafka_utils.kafka import KafkaUtils
from utils.minio_utils.minio import MinioClient

class DataExtractor:
    def __init__(self, bucket_name):
        self.minioClient = MinioClient()
        self.bucket_name = bucket_name

        self.API_ENDPOINT = os.getenv("API_ENDPOINT_SCORM")           # Trả về None nếu biến không tồn tại
        self.API_KEY = os.environ.get("API_KEY_SCORM") 
        self.API_SECRET = os.environ.get("API_SECRET_SCORM") 

        kafkaClient = KafkaUtils()
        self.consumer = kafkaClient.create_consumer(bootstrapServers=os.getenv("BOOTSTRAPSERVERS"), topic='demo_java')
    
    def extractData(self):
        records = self.consumer.poll(timeout_ms=1000)
        return records
    

   