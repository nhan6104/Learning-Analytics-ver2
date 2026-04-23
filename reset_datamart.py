from utils.pgsql_utils import db

def reset_datamart():
    print("Dropping datamart schema...")
    try:
        db.execute_query("DROP SCHEMA IF EXISTS datamart CASCADE")
        print("Datamart schema dropped successfully.")
    except Exception as e:
        print(f"Error dropping schema: {e}")

if __name__ == "__main__":
    reset_datamart()
