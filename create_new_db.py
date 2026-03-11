import psycopg2
import os
from dotenv import load_dotenv

def create_database(new_db_name):
    # Load environment variables from .env file
    load_dotenv()

    # Get connection details for the existing database (to execute CREATE DATABASE)
    host = os.getenv("PGSQL_HOST")
    port = os.getenv("PGSQL_PORT")
    user = os.getenv("PGSQL_USER")
    password = os.getenv("PGSQL_PASSWORD")
    ssl_mode = os.getenv("PGSQL_SSL_MODE", "prefer")
    ssl_root_cert = os.getenv("PGSQL_SSL_ROOT_CERT")
    
    # We must connect to an existing database to create a new one. 
    # Usually 'postgres' or the current 'defaultdb' from .env
    existing_db = os.getenv("PGSQL_DBNAME", "postgres")

    try:
        # 1. Connect to the existing database
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=existing_db,
            user=user,
            password=password,
            sslmode=ssl_mode,
            sslrootcert=ssl_root_cert
        )
        
        # 2. Set autocommit to True because CREATE DATABASE cannot run inside a transaction
        conn.autocommit = True
        
        cursor = conn.cursor()
        
        # 3. Execute the CREATE DATABASE command
        # Note: We use string formatting for the database name because it cannot be passed as a parameter
        # to the execute method in this specific case.
        print(f"Creating database: {new_db_name}...")
        cursor.execute(f'CREATE DATABASE "{new_db_name}";')
        
        print(f"Successfully created database '{new_db_name}'.")
        
        cursor.close()
        conn.close()
        
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    # You can change the database name here
    db_name = input("Enter the name of the new database: ")
    if db_name.strip():
        create_database(db_name.strip())
    else:
        print("Database name cannot be empty.")
