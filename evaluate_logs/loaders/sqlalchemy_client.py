import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()


class SQLAlchemyClient:
    def __init__(self):
        db_url = os.getenv("POSTGRES_URI")
        print(f"Using POSTGRES_URI: {db_url}")
        if not db_url:
            host = os.getenv("PG_HOST", "localhost")
            port = os.getenv("PG_PORT", "5432")
            user = os.getenv("PG_USER", "postgres")
            pwd = os.getenv("PG_PASSWORD", "postgres")
            db = os.getenv("PG_DATABASE", "postgres")
            db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"
        self.engine = create_engine(db_url)

    def run_sql(self, sql: str):
        with self.engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
        return df.to_dict(orient="records")
