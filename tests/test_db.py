from datetime import datetime

import psycopg2

conn = psycopg2.connect(
    dbname="plantdata",
    user="cropps",
    password="cropps123",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

cur.execute("""
            INSERT INTO plant_logs (timestamp, yellow_pixels, agitation, normalized_pixels, image_path)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (datetime.now(), 1234, True, 0.85, "/app/shared-images/image1.png"))

conn.commit()
cur.close()
conn.close()
print("Inserted test data.")
