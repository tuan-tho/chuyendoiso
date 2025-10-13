# app/database.py
import os
from dotenv import load_dotenv # type: ignore
from sqlalchemy import create_engine # pyright: ignore[reportMissingImports]
from sqlalchemy.orm import sessionmaker, declarative_base, Session # type: ignore

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Gợi ý: trong .env, chuỗi kết nối kiểu:
# mssql+pyodbc://USER:PASSWORD@SERVER\INSTANCE/DB?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,                  # True nếu muốn log SQL
    future=True,
    # Hai tuỳ chọn giúp an toàn/ổn định hơn với NVARCHAR(MAX) + hiệu năng
    connect_args={},
    use_setinputsizes=False,     # tránh set input sizes gây lỗi với NVARCHAR(MAX) ở vài bản pyodbc
    fast_executemany=True,       # tăng tốc bulk insert (không ảnh hưởng Unicode)
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
