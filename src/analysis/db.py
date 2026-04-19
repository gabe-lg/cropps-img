import os
from datetime import datetime

import psycopg2


def insert_data(yellow_pixels, agitation, normalized_pixels, image_path):
    password = os.getenv("DB_PASSWORD")
    if not password:
        print("[DB] DB_PASSWORD env var not set; skipping insert.")
        return
    try:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME", "plantdata"),
            user=os.getenv("DB_USER", "cropps"),
            password=password,
            host=os.getenv("DB_HOST", "postgres-db"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()

        cur.execute("""
                    INSERT INTO plant_logs (timestamp, yellow_pixels, agitation, normalized_pixels, image_path)
                    VALUES (%s, %s, %s, %s, %s)
                    """, (datetime.now(), yellow_pixels, agitation,
                          normalized_pixels, image_path))

        conn.commit()
        cur.close()
        conn.close()
        print("[DB] Log inserted.")
    except Exception as e:
        print(f"[DB] Error inserting log: {e}")
