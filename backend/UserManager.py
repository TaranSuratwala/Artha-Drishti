import logging
import os
import requests
from sqlalchemy import text, create_engine
from werkzeug.security import generate_password_hash, check_password_hash
import datetime

logger = logging.getLogger(__name__)

class UserManager:
    """
    Manages user authentication and persistence in PostgreSQL.
    """
    def __init__(self, engine):
        self.engine = engine
        self._init_users_table()

    def _init_users_table(self):
        """Initialize Users table if not exists"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS users (
                        id SERIAL PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(120) UNIQUE NOT NULL,
                        password_hash VARCHAR(255) NOT NULL,
                        auth_provider VARCHAR(20) DEFAULT 'local',
                        google_id VARCHAR(255),
                        avatar_url VARCHAR(500),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))
                # Index for performance
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                """))
                conn.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id);
                """))
                # Add new columns if table already exists (migration-safe)
                for col, typedef in [
                    ('auth_provider', "VARCHAR(20) DEFAULT 'local'"),
                    ('google_id', 'VARCHAR(255)'),
                    ('avatar_url', 'VARCHAR(500)'),
                ]:
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {typedef};"))
                    except Exception:
                        pass  # column may already exist on older PG
        except Exception as e:
            logger.error(f"Error initializing users table: {e}")

    def create_user(self, username, email, password):
        """Register a new user"""
        password_hash = generate_password_hash(password)
        try:
            with self.engine.begin() as conn:
                # Check if exists
                res = conn.execute(text("SELECT id FROM users WHERE username=:u OR email=:e"), 
                                  {'u': username, 'e': email}).fetchone()
                if res:
                    return {"error": "Username or Email already exists"}
                
                # Insert
                result = conn.execute(text("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (:u, :e, :p)
                    RETURNING id, username, email
                """), {'u': username, 'e': email, 'p': password_hash})
                
                row = result.fetchone()
                return {
                    "id": row.id,
                    "username": row.username,
                    "email": row.email
                }
        except Exception as e:
            logger.error(f"Create User Error: {e}")
            return {"error": str(e)}

    def verify_user(self, username, password):
        """Verify credentials and return user info"""
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT id, username, password_hash FROM users WHERE username=:u"), 
                                  {'u': username}).fetchone()
                
                if res and check_password_hash(res.password_hash, password):
                    return {
                        "id": res.id,
                        "username": res.username
                    }
                return None
        except Exception as e:
            logger.error(f"Verify User Error: {e}")
            return None

    def get_user_by_id(self, user_id):
        """Get user details by ID"""
        try:
            # JWT identity can be a string, convert to int
            uid = int(user_id) if isinstance(user_id, str) else user_id
            with self.engine.connect() as conn:
                res = conn.execute(text("SELECT id, username, email, auth_provider, avatar_url FROM users WHERE id=:i"), 
                                  {'i': uid}).fetchone()
                if res:
                    return {
                        "id": res.id,
                        "username": res.username,
                        "email": res.email,
                        "auth_provider": getattr(res, 'auth_provider', 'local') or 'local',
                        "avatar_url": getattr(res, 'avatar_url', None),
                    }
                return None
        except Exception as e:
            logger.error(f"Get User Error: {e}")
            return None

    # ─── Google OAuth ─────────────────────────────────────────────────

    def verify_google_token(self, credential):
        """Verify a Google OAuth2 ID token (from @react-oauth/google) and
        return / create the corresponding local user."""
        try:
            # Verify with Google's tokeninfo endpoint
            resp = requests.get(
                'https://oauth2.googleapis.com/tokeninfo',
                params={'id_token': credential},
                timeout=10,
            )
            if resp.status_code != 200:
                return {"error": "Invalid Google token"}

            payload = resp.json()
            google_id = payload.get('sub')
            email = payload.get('email')
            name = payload.get('name', email.split('@')[0] if email else 'user')
            avatar = payload.get('picture')

            if not email:
                return {"error": "Email not available from Google"}

            with self.engine.begin() as conn:
                # Check if user already linked by google_id
                row = conn.execute(
                    text("SELECT id, username, email FROM users WHERE google_id=:gid"),
                    {'gid': google_id}
                ).fetchone()

                if row:
                    return {"id": row.id, "username": row.username, "email": row.email}

                # Check if email already registered (link accounts)
                row = conn.execute(
                    text("SELECT id, username, email FROM users WHERE email=:e"),
                    {'e': email}
                ).fetchone()

                if row:
                    # Link existing account to Google
                    conn.execute(
                        text("UPDATE users SET google_id=:gid, auth_provider='google', avatar_url=:av WHERE id=:uid"),
                        {'gid': google_id, 'av': avatar, 'uid': row.id}
                    )
                    return {"id": row.id, "username": row.username, "email": row.email}

                # Create new user via Google
                # Generate a unique username from the name
                base_username = name.replace(' ', '_').lower()[:40]
                username = base_username
                counter = 1
                while True:
                    existing = conn.execute(
                        text("SELECT id FROM users WHERE username=:u"), {'u': username}
                    ).fetchone()
                    if not existing:
                        break
                    username = f"{base_username}_{counter}"
                    counter += 1

                dummy_hash = generate_password_hash('__google_oauth__')
                result = conn.execute(text("""
                    INSERT INTO users (username, email, password_hash, auth_provider, google_id, avatar_url)
                    VALUES (:u, :e, :p, 'google', :gid, :av)
                    RETURNING id, username, email
                """), {'u': username, 'e': email, 'p': dummy_hash, 'gid': google_id, 'av': avatar})

                row = result.fetchone()
                return {"id": row.id, "username": row.username, "email": row.email}

        except requests.RequestException as e:
            logger.error(f"Google token verification network error: {e}")
            return {"error": "Failed to verify Google token"}
        except Exception as e:
            logger.error(f"Google OAuth Error: {e}")
            return {"error": str(e)}
