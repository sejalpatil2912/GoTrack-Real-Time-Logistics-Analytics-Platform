import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-logistics'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'root' # Blank by default on local xampp/wamp
    MYSQL_DB = 'logistics_db'
    MYSQL_CURSORCLASS = 'DictCursor' # Returns rows as dictionaries for easier pandas/template handling
