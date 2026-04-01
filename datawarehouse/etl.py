from datawarehouse.extract import DataExtractor
from datawarehouse.load import DataLoader
from datawarehouse.transform import DataTransformer
import json
import pandas as pd


class ETLProcess:
    def __init__(self):
        self.extractor = DataExtractor()
        self.transformer = DataTransformer()
        self.loader = DataLoader()

    def execute(self, date_to_extract: str, range_time_to_extract = None):
        # Extract
        object_names = self.extractor.getObjectNames(date_to_extract, range_time_to_extract)
        
        for object_name in object_names:
            raw_data = self.extractor.extractData(object_name)
            
            for data in raw_data:
                # Transform
                transformed_data = self.transformer.executeTransform(data)
            
                # Load
                self.loader.load_data([transformed_data])


    def execute_test_pipeline(self):
        
        with open("steady_scaled.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)

        group_data = {}
        for data in raw_data:
            registration = data.get("context", {}).get("registration", "")
            if registration not in group_data:
                group_data[registration] = []
            group_data[registration].append(data)

        

        for registration, data_list in group_data.items():
            # Transform
            transformed_data = self.transformer.transform(data_list)

            # Load
            self.loader.load_data(transformed_data)

if __name__ == "__main__":
    etl  = ETLProcess()
    etl.execute_test_pipeline()
    