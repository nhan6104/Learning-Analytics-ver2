from tkinter import INSERT

import psycopg2
import os
from dotenv import load_dotenv
load_dotenv()

class PostgresDB:

    def __init__(self):
        self.schema = "" 

    def get_connection (self):
        try :
            connection = psycopg2.connect(
                host=os.getenv("PGSQL_HOST"),
                port=os.getenv("PGSQL_PORT"),
                dbname=os.getenv("PGSQL_DBNAME"),
                user=os.getenv("PGSQL_USER"),
                password=os.getenv("PGSQL_PASSWORD"),
                sslmode=os.getenv("PGSQL_SSL_MODE", "prefer"),
                sslrootcert=os.getenv("PGSQL_SSL_ROOT_CERT")
            )

            return connection
        
        except psycopg2.Error as e:
            print(f"Error connecting to PostgreSQL: {e}")
            return False

    def create_schema(self, schema_name):
        query = f"""CREATE SCHEMA IF NOT EXISTS {schema_name};"""
        
        connection = self.get_connection()

        with connection.cursor() as cursor:
            cursor.execute(query)
            connection.commit()

        connection.close()

        self.schema = schema_name

    def create_table (self, table_name, schema):
        query = f"CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} ({schema})"
        connection = self.get_connection()

        with connection.cursor() as cursor:
            cursor.execute(query)
            connection.commit()

        connection.close()


    def execute_query(self, query, params=None):
        connection = self.get_connection()
        result = None
        with connection.cursor() as cursor:
            cursor.execute(query, params)
            if cursor.description:
                result = cursor.fetchall()
            connection.commit()

        connection.close()

        return result
    
    def insert_record(self, table_name, object):
        keys = list(object.keys())
        columns = ', '.join(keys)
        placeholders = ",".join(["%s"] * len(keys))

        query = f"""
            INSERT INTO {self.schema}.{table_name} ({columns})
            VALUES ({placeholders}) 
            """
        values = tuple(object[k] for k in keys)
        
        connection = self.get_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            connection.commit()

        connection.close()

    def update_record(self, table_name, object, condition_column, condition_value):
        keys = list(object.keys())
        columns = ', '.join(keys)
        placeholders = ",".join(["%s"] * len(keys))

        query = f"""
            UPDATE {self.schema}.{table_name} 
            SET {columns} = {placeholders}
            WHERE {condition_column} = %s
            """ 
        
        values = tuple(object[k] for k in keys) + (condition_value, )
        
        connection = self.get_connection()
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            connection.commit()

        connection.close()
    
    def get_schema_name (self):
        return self.schema
    
    def insert_many_records(self, table_name, objects, condition = None):

        keys = list(objects[0].keys())
        columns = ', '.join(keys)
        placeholders = ",".join(["%s"] * len(keys))
        
        query = f"""
            INSERT INTO {self.schema}.{table_name} ({columns})
            VALUES ({placeholders}) 
        """
        if condition is not None:
            query += condition


        values = [tuple(obj[k] for k in keys) for obj in objects]
        
        connetcion = self.get_connection()
        with connetcion.cursor() as cursor:
            cursor.executemany(query, values)
            connetcion.commit()

        connetcion.close()

db = PostgresDB()