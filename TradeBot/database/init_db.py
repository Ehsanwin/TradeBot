from __future__ import annotations
from .session import init_db

def init_database() -> None:
    """Initialize the database schema and tables."""
    try:
        init_db()
        print("✅ Database initialized successfully. Tables created (or already exist).")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        raise

def main() -> None:
    init_database()

if __name__ == "__main__":
    main()
