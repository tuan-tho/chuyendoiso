from sqlalchemy import create_engine, text # type: ignore
from dotenv import load_dotenv # type: ignore
import os

load_dotenv()
url = os.getenv("DATABASE_URL")
print("🔗 Connecting to:", url)
engine = create_engine(url)

try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT DB_NAME(), @@VERSION")).fetchone()
        print("✅ Connected to:", result)
except Exception as e:
    print("❌ Error:", e)
