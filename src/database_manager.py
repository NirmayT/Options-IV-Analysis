from sqlalchemy import create_engine, text

engine = create_engine("sqlite:///database/options.db")

with engine.connect() as connection:
    connection.execute(text("SELECT 1"))  # Test the connection

print("Database connection established.")