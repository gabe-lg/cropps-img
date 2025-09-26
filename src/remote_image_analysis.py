import os, io, zipfile, requests

REDCLOUD_ENDPOINT = "http://128.84.40.199:3000/analyze"

def remote_image_analysis(directory: str, server_url=REDCLOUD_ENDPOINT):
    print(f"[INFO] Preparing to send images from directory: {directory}")

    # Pack images into a zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            if os.path.isfile(fpath):
                print(f"[DEBUG] Adding file to archive: {fpath}")
                zipf.write(fpath, arcname=fname)

    zip_buffer.seek(0)
    print(f"[INFO] Finished zipping images. Size = {len(zip_buffer.getvalue())/1024:.2f} KB")

    # Send to server
    print(f"[INFO] Sending files to {server_url}")
    files = {"images": ("images.zip", zip_buffer, "application/zip")}
    resp = requests.post(server_url, files=files)

    print(f"[INFO] Response status code: {resp.status_code}")
    resp.raise_for_status()

    result = resp.json().get("result")
    print(f"[INFO] Received result: {result}")

    return result
