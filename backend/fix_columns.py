"""Add missing columns to users table for Google OAuth support."""
from sqlalchemy import create_engine, text

DB_URL = "postgresql://postgres:Taran%4017@localhost:5432/StockDB"
engine = create_engine(DB_URL)

with engine.begin() as conn:
    # Check current columns
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
    ))
    columns = [row[0] for row in result]
    print(f"Current columns: {columns}")

    # Add missing columns
    migrations = [
        ("auth_provider", "VARCHAR(20) DEFAULT 'local'"),
        ("google_id", "VARCHAR(255)"),
        ("avatar_url", "VARCHAR(500)"),
    ]
    for col, typedef in migrations:
        if col not in columns:
            print(f"Adding column: {col} {typedef}")
            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {typedef}"))
        else:
            print(f"Column '{col}' already exists")

    # Create index on google_id if not exists
    conn.execute(text("CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id)"))
    print("Done! google_id index ensured.")

    # Verify
    result = conn.execute(text(
        "SELECT column_name FROM information_schema.columns WHERE table_name='users' ORDER BY ordinal_position"
    ))
    print(f"Updated columns: {[row[0] for row in result]}")
