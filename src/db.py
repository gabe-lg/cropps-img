import os
import psycopg2
from datetime import datetime

def insert_data(yellow_pixels, agitation, normalized_pixels, image_path):
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "plantdata"),
            user=os.getenv("DB_USER", "cropps"),
            password=os.getenv("DB_PASSWORD", "cropps123"),
            host=os.getenv("DB_HOST", "postgres-db"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()

        cur.execute("""
            INSERT INTO plant_logs (timestamp, yellow_pixels, agitation, normalized_pixels, image_path)
            VALUES (%s, %s, %s, %s, %s)
        """, (datetime.now(), yellow_pixels, agitation, normalized_pixels, image_path))

        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Log inserted.")
    except Exception as e:
        print(f"[DB] Error inserting log: {e}")
