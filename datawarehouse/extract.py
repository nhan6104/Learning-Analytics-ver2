import os
from utils.minio_utils.minio import MinioClient
from dotenv import load_dotenv
load_dotenv()

class DataExtractor:
    def __init__(self):
        self.minioClient = MinioClient()
        self.bucket_name = os.getenv("MINIO_BUCKET_NAME")

    def getObjectNames(self, date_to_extract: str, range_time_to_extract = None):
        """
            date_to_extract: Date which want to extract data
            range_time_to_extract: Range time in Date want to extract
        """
        # clean_date = str(date_to_extract).split(' ')[0].replace('-', '/')
        # print(date_to_extract, self.bucket_name)
        object_names = self.minioClient.get_objects_name(self.bucket_name, prefix=date_to_extract)
        return object_names
    
    def extractData(self, object_name: str):
        """
            object_name: Object name want to extract data
        """
        data = self.minioClient.get_object(bucket_name = self.bucket_name, object_name = object_name)
        return data.json()
    
    