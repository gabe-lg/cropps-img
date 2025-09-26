from flask import Flask, request, jsonify
import tempfile, zipfile, os, shutil
from image_analysis import image_analysis  # import your existing function

app = Flask(__name__)

@app.route("/analyze", methods=["POST"])
def analyze():
    print(f"[*] Received request from {request.remote_addr}")
    if "images" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    # Save uploaded zip temporarily
    tmp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(tmp_dir, "images.zip")
    request.files["images"].save(zip_path)

    # Unzip
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(tmp_dir)

    # Run analysis
    try:
        # print amount of files extracted
        num_files = len(os.listdir(tmp_dir))
        print(f"[*] Running analysis on {num_files} files")
        result = image_analysis(tmp_dir)
        print(f"[+] Analysis result: {result}")
        return jsonify({"result": result})
    except Exception as e:
        print(f"[!] Error during analysis: {e}")
        return jsonify({"error": "Analysis failed"}), 500
    finally:
        shutil.rmtree(tmp_dir)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000)
