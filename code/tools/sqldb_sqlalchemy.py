from langchain_community.utilities import SQLDatabase

def get_sql_db(uri: str) -> SQLDatabase:
    return SQLDatabase.from_uri(uri)
