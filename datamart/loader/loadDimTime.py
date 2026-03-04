from utils.pgsql_utils import db

class LoadDimTime:
    def __init__(self):
        self.datawarhouse_name = "datawarehouse"
        self.datamart_name = "datamart"
        self.db = db

    def load(self):
        query = f"""INSERT INTO {self.datamart_name}.dim_time (
                        time_id,
                        date,
                        month,
                        year,
                        week,
                        day_of_week,
                        time_slot
                    )
                    SELECT 
                        time_id,
                        date,
                        month,
                        year,
                        week,
                        day_of_week,
                        time_slot
                    FROM {self.datawarhouse_name}.dim_time
                """
        db.execute_query(query)
    