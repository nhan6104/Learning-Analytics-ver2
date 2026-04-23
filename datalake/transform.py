import json
import pandas as pd
import ast

class DataTransformer:
    def __init__(self):
        pass

    def arrange_data(self, records):
        unordered_data = []
        for msg in records:
            
            print((msg.value.decode('utf-8')))
            if msg.value.decode('utf-8'):
                raw = msg.value.decode('utf-8')
                clean_data = ast.literal_eval(raw)
                print(clean_data)
                json_str = json.dumps(clean_data)
                datajson = json.loads(json_str)
                data = {
                    "time_stamp": datajson["timestamp"],
                    "data": json.dumps(datajson)
                }
                unordered_data.append(data)

        df = pd.DataFrame(unordered_data)

        df["time_parsed"] = pd.to_datetime(
            df["time_stamp"],
            format="%Y-%m-%dT%H:%M:%S.%fZ",
            utc=True
        )

        ordered_data = (
            df
            .sort_values("time_parsed")["data"]
            .apply(json.loads)
            .tolist()
        )

        return ordered_data

    def transform(self, records):
        ordered_data = self.arrange_data(records)
        return ordered_data