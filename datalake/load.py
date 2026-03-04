import datetime
from utils.minio_utils.minio import MinioClient
import os
import json
import io


class DataLoader:
    def __init__(self):
        self.minio_client = MinioClient()
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME")

    def load(self, data):
        json_bytes = json.dumps(data).encode('utf-8')

        found = self.minio_client.check_bucket_exists(bucket_name=self.bucket_name)
        if not found:
            self.minio_client.create_bucket(bucket_name=self.bucket_name)
            print("Created bucket", self.bucket_name)
        else:
            print("Bucket", self.bucket_name, "already exists")

        clean_date = str(datetime.datetime.now().date()).replace('-', '/')
        clean_time = str(datetime.datetime.now().time()).split('.')[0]

        self.minio_client.put_object(
            bucket_name=self.bucket_name,
            destination_file=f'{clean_date}/{clean_time}_log_xAPI.json',
            data=io.BytesIO(json_bytes),
            length_data=len(json_bytes)
        )

        return "Data loaded to MinIO successfully."
    
