import json
import pandas as pd

class DataTransformer:
    def __init__(self):
        pass

    def arrange_data(self, records):
        unordered_data = []
        for _, msgs in records.items():
            for msg in msgs:

                print(msg.value.decode('utf-8')[0])

                if msg.value.decode('utf-8')[0] == '{':
                    datajson = json.loads(msg.value.decode('utf-8').replace('\'', '\"'))
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