from utils.pgsql_utils import db

class LoadDimActor:
    def __init__(self):
        self.datawarhouse_name = "datawarehouse"
        self.datamart_name = "datamart"

    def load(self):
        query = f"""INSERT INTO {self.datamart_name}.dim_actor (
            actor_id,
            actor_name
        )
        SELECT 
            actor_id,
            actor_name
        FROM {self.datawarhouse_name}.dim_actor
        """
        return query