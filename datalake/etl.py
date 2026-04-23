
from datalake.extract import DataExtractor
from datalake.transform import DataTransformer
from datalake.load import DataLoader

class ETLProcessor:
    def __init__(self):
        self.extractor = DataExtractor()
        self.transformer = DataTransformer()
        self.loader = DataLoader()

    def execute(self):
        # Extract
        records = self.extractor.extractData()
        
        # Transform
        transformed_data = self.transformer.transform(records)
        
        # Load
        self.loader.load(transformed_data)


ETLProcessor().execute()