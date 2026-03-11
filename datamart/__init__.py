from utils.pgsql_utils import db

schema_name = "datamart"
db.create_schema(schema_name)