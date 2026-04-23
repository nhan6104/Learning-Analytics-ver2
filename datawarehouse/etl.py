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

    def execute(self, date_to_extract):
        # Extract
        object_names = self.extractor.getObjectNames(date_to_extract)
        for object_name in object_names:
            raw_data_list = self.extractor.extractData(object_name)
            print(object_names)

            # Transform
            transformed_data = self.transformer.transform(raw_data_list)
        
            # Load
            self.loader.load_data(transformed_data)


ETLProcess().execute("2026/03/22")
    