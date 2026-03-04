from utils.pgsql_utils import db

schema_name = "datawarehouse"
db.create_schema(schema_name)