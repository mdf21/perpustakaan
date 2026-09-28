import sqlite3
import os

db_path = os.path.join('instance', 'perpustakaan.db')

if not os.path.exists(db_path):
    print("Database not found. Probably hasn't been initialized yet.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if cover_image exists
    cursor.execute("PRAGMA table_info(buku)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'cover_image' not in columns:
        print("Adding cover_image column to buku table...")
        cursor.execute("ALTER TABLE buku ADD COLUMN cover_image VARCHAR(255)")
        conn.commit()
        print("Column cover_image added successfully.")
    else:
        print("Column cover_image already exists.")
        
    conn.close()
