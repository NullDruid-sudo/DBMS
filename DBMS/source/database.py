

import mysql.connector
from mysql.connector import pooling, Error
from datetime import datetime, timedelta
import uuid
import config


# Connection Pool 

_pool = None


def _get_pool():
    
    global _pool
    if _pool is None:
        try:
            conn = mysql.connector.connect(
                host=config.MYSQL_HOST,
                user=config.MYSQL_USER,
                password=config.MYSQL_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}`"
            )
            conn.commit()
            cursor.close()
            conn.close()
        except Error as e:
            print(f"[DB] Error creating database: {e}")
            raise

        _pool = pooling.MySQLConnectionPool(
            pool_name="digilocker_pool",
            pool_size=5,
            host=config.MYSQL_HOST,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE
        )
    return _pool


def get_db():
    """Get a connection from the pool."""
    return _get_pool().get_connection()


# initialization

def init_db():
    """Create all tables if they don't exist."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INT AUTO_INCREMENT PRIMARY KEY,
            name        VARCHAR(100) NOT NULL,
            email       VARCHAR(150) NOT NULL UNIQUE,
            password    VARCHAR(255) NOT NULL,
            aadhaar     VARCHAR(12),
            phone       VARCHAR(15),
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            doc_id      INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            file_name   VARCHAR(255) NOT NULL,
            file_path   VARCHAR(500) NOT NULL,
            file_size   BIGINT DEFAULT 0,
            file_type   VARCHAR(50),
            category    VARCHAR(50) DEFAULT 'Other',
            is_verified TINYINT DEFAULT 0,
            upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shared_links (
            share_id    INT AUTO_INCREMENT PRIMARY KEY,
            doc_id      INT NOT NULL,
            token       VARCHAR(64) NOT NULL UNIQUE,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at  DATETIME,
            is_active   TINYINT DEFAULT 1,
            FOREIGN KEY (doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            log_id      INT AUTO_INCREMENT PRIMARY KEY,
            user_id     INT NOT NULL,
            action      VARCHAR(50) NOT NULL,
            detail      VARCHAR(500),
            timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()
    print("[DB] All tables initialized successfully.")


# User Operations 

def add_user(name, email, password_hash, aadhaar=None, phone=None):
    """Register a new user. Returns user_id or None if email exists."""
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (name, email, password, aadhaar, phone) "
            "VALUES (%s, %s, %s, %s, %s)",
            (name, email, password_hash, aadhaar, phone)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return user_id
    except Error as e:
        if e.errno == 1062:  # Duplicate entry
            return None
        raise
    finally:
        cursor.close()
        conn.close()


def get_user_by_email(email):
    """Fetch a user by email. Returns dict or None."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def get_user_by_id(user_id):
    """Fetch a user by ID. Returns dict or None."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    return user


def update_user_profile(user_id, name=None, aadhaar=None, phone=None):
    """Update user profile fields."""
    conn = get_db()
    cursor = conn.cursor()
    fields = []
    values = []
    if name is not None:
        fields.append("name = %s")
        values.append(name)
    if aadhaar is not None:
        fields.append("aadhaar = %s")
        values.append(aadhaar)
    if phone is not None:
        fields.append("phone = %s")
        values.append(phone)
    if not fields:
        cursor.close()
        conn.close()
        return
    values.append(user_id)
    cursor.execute(
        f"UPDATE users SET {', '.join(fields)} WHERE user_id = %s", values
    )
    conn.commit()
    cursor.close()
    conn.close()


# Document Operations 

def add_document(user_id, file_name, file_path, file_size, file_type, category="Other"):
    """Insert a new document record. Returns doc_id."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (user_id, file_name, file_path, file_size, file_type, category) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, file_name, file_path, file_size, file_type, category)
    )
    conn.commit()
    doc_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return doc_id


def get_user_documents(user_id, category=None, search=None):
    """Get all documents for a user, optionally filtered."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT * FROM documents WHERE user_id = %s"
    params = [user_id]
    if category and category != "All":
        query += " AND category = %s"
        params.append(category)
    if search:
        query += " AND file_name LIKE %s"
        params.append(f"%{search}%")
    query += " ORDER BY upload_date DESC"
    cursor.execute(query, params)
    docs = cursor.fetchall()
    cursor.close()
    conn.close()
    return docs


def get_document_by_id(doc_id):
    """Get a single document by ID."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM documents WHERE doc_id = %s", (doc_id,))
    doc = cursor.fetchone()
    cursor.close()
    conn.close()
    return doc


def delete_document(doc_id, user_id):
    """Delete a document (only if owned by user). Returns True if deleted."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM documents WHERE doc_id = %s AND user_id = %s",
        (doc_id, user_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    cursor.close()
    conn.close()
    return deleted


def get_user_stats(user_id):
    """Get stats for the dashboard."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute(
        "SELECT COUNT(*) as total_docs, COALESCE(SUM(file_size), 0) as total_size "
        "FROM documents WHERE user_id = %s", (user_id,)
    )
    stats = cursor.fetchone()

    cursor.execute(
        "SELECT COUNT(*) as shared_count FROM shared_links sl "
        "JOIN documents d ON sl.doc_id = d.doc_id "
        "WHERE d.user_id = %s AND sl.is_active = 1", (user_id,)
    )
    shared = cursor.fetchone()
    stats['shared_count'] = shared['shared_count']

    cursor.execute(
        "SELECT category, COUNT(*) as count FROM documents "
        "WHERE user_id = %s GROUP BY category", (user_id,)
    )
    stats['categories'] = cursor.fetchall()

    cursor.close()
    conn.close()
    return stats


# Shared Links 

def create_share_link(doc_id, hours=24):
    """Create a shareable link token for a document. Returns token."""
    token = uuid.uuid4().hex
    expires = datetime.now() + timedelta(hours=hours)
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO shared_links (doc_id, token, expires_at) VALUES (%s, %s, %s)",
        (doc_id, token, expires)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return token


def get_shared_document(token):
    """Get document info via share token. Returns dict or None."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT d.*, sl.expires_at, sl.is_active FROM shared_links sl "
        "JOIN documents d ON sl.doc_id = d.doc_id "
        "WHERE sl.token = %s", (token,)
    )
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    if result:
        if not result['is_active']:
            return None
        if result['expires_at'] and result['expires_at'] < datetime.now():
            return None
    return result


def deactivate_share_link(token, user_id):
    """Deactivate a share link (only if user owns the document)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE shared_links sl JOIN documents d ON sl.doc_id = d.doc_id "
        "SET sl.is_active = 0 WHERE sl.token = %s AND d.user_id = %s",
        (token, user_id)
    )
    conn.commit()
    cursor.close()
    conn.close()


# Activity Log 

def log_activity(user_id, action, detail=""):
    """Log a user action."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO activity_log (user_id, action, detail) VALUES (%s, %s, %s)",
        (user_id, action, detail)
    )
    conn.commit()
    cursor.close()
    conn.close()


def get_recent_activity(user_id, limit=10):
    """Get recent activity for a user."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT * FROM activity_log WHERE user_id = %s "
        "ORDER BY timestamp DESC LIMIT %s",
        (user_id, limit)
    )
    activity = cursor.fetchall()
    cursor.close()
    conn.close()
    return activity