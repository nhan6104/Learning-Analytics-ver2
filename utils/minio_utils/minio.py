from minio import Minio
import os
from dotenv import load_dotenv
load_dotenv()
import datetime

minioClient = Minio(
        endpoint=os.getenv("MINIO_ENDPOINT"),
        access_key=os.getenv("MINIO_ACCESS_KEY"),
        secret_key=os.getenv("MINIO_SECRET_KEY"),
        secure=False
    )

class MinioClient:
    def __init__(self):
       self.minio_client = minioClient

    def check_bucket_exists(self, bucket_name):
        return self.minio_client.bucket_exists(bucket_name=bucket_name)   
    
    def create_bucket(self, bucket_name):
        self.minio_client.make_bucket(bucket_name=bucket_name)

    def put_object(self, bucket_name, destination_file, data, length_data = 5 * 1024 * 1024):            
        self.minio_client.put_object(
            bucket_name=bucket_name,
            object_name=destination_file,
            data=data,
            length=length_data,
        )           

    def get_object(self, bucket_name, object_name):
        if self.minio_client.bucket_exists(bucket_name):
            data = self.minio_client.get_object(
                bucket_name=bucket_name,
                object_name=object_name
            )

            return data

    def get_objects_name(self, bucket_name, prefix = None, recursive = True):
        objects = self.minio_client.list_objects(bucket_name=bucket_name, prefix=prefix, recursive=recursive)
        objects_name = [obj.object_name for obj in objects]
        return objects_name


if __name__ == '__main__':
        # lst_object = minioClient.list_objects(bucket_name='logsystem', prefix=None, recursive=False)
        # print(list(lst_object))
        # for obj in lst_object:
        #     print(obj.object_name)
        # if self.minio_client.bucket_exists():
        #     data = self.minio_client.get_object(
        #         bucket_name=bucket_name,
        #         object_name=destination_files
        #     )
        data = minioClient.get_object(
                bucket_name='logsystem',
                object_name='2025/10/24/20:26:44_log_xAPI.json'
            )
        
        
        print(len(data.json()))