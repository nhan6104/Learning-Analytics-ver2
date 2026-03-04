import pymysql
import os
import logging
from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class MoodleDatabase:
    def __init__(self):
        pass

    def _is_mysql_connection_alive(self, conn) -> bool:
            """Check if MySQL connection is alive"""
            try:
                conn.ping(reconnect=False)
                return True
            except:
                return False
            
    def get_mysql_connection(self):
        """Get or create MySQL connection"""
        # if  not self._is_mysql_connection_alive(self.mysql_conn):
        try:
            mysql_conn = pymysql.connect(
                host=os.getenv("MOODLE_DB_HOST"),
                port=int(os.getenv("MOODLE_DB_PORT")),
                user=os.getenv("MOODLE_DB_USER"),
                password=os.getenv("MOODLE_DB_PASSWORD"),
                database=os.getenv("MOODLE_DB_NAME"),
                autocommit=False,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("Connected to MySQL")
        except Exception as e:
            logger.error(f"Error connecting to MySQL: {e}")
            raise

        return mysql_conn
    
    def inquiry_query(self, query, params=None):
        """Inquiry a query and return results"""
        mysql_conn = self.get_mysql_connection()
        try:
            with mysql_conn.cursor() as cursor:
                cursor.execute(query, params)
                result = cursor.fetchall()

            mysql_conn.close()                
            return result
            
        except Exception as e:
            logger.error(f"Error executing MySQL query: {e}")
            if mysql_conn:
                mysql_conn.rollback()
            raise
        
            
 
moodle_db = MoodleDatabase()