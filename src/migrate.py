"""
One-time migration: adds risk_free_rate and dividend_yield columns to an
EXISTING options.db. Only needed if you want to keep old snapshots instead of
deleting the database. Safe to run multiple times (skips columns that exist).

Run:  python migrate.py     (then you can delete this file)
"""

from sqlalchemy import create_engine, text
import config

engine = create_engine(f"sqlite:///{config.DATABASE_NAME}", echo=False)

TABLES = [
    config.RAW_OPTIONS_TABLE,
    config.CLEAN_OPTIONS_TABLE,
    config.ANALYTICS_OPTIONS_TABLE,
]
NEW_COLUMNS = ("risk_free_rate", "dividend_yield")


def main():
    with engine.begin() as conn:
        for table in TABLES:
            for col in NEW_COLUMNS:
                try:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} REAL"))
                    print(f"Added {col} to {table}")
                except Exception as e:
                    print(f"Skipped {table}.{col}: {e}")
    print("Migration complete.")


if __name__ == "__main__":
    main()
