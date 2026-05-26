"""LiveCap 视频剪辑 Web 服务"""

import os
import uuid
import shutil

from flask import Flask, request, jsonify, send_from_directory, send_file

from agent import clip_video, concat_videos, change_speed, VideoEditor

app = Flask(__name__, static_folder="static")

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/upload", methods=["POST"])
def upload_video():
    """上传视频文件"""
    if "file" not in request.files:
        return jsonify({"error": "未找到文件"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "文件名为空"}), 400

    ext = os.path.splitext(file.filename)[1] or ".mp4"
    file_id = uuid.uuid4().hex
    filename = f"{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    return jsonify({"id": file_id, "filename": filename})


@app.route("/api/videos/<filename>")
def serve_video(filename):
    """提供视频文件访问"""
    # 先查 uploads，再查 outputs
    for folder in [UPLOAD_DIR, OUTPUT_DIR]:
        path = os.path.join(folder, filename)
        if os.path.isfile(path):
            return send_file(path)
    return jsonify({"error": "文件不存在"}), 404


@app.route("/api/edit", methods=["POST"])
def edit_video():
    """
    视频剪辑接口
    请求体 JSON:
    {
      "source": "上传后的文件名",
      "segments": [{"start": "00:00:01", "end": "00:00:05"}, ...],
      "speed": 1.0  // 可选
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "请求体为空"}), 400

    source = data.get("source")
    segments = data.get("segments", [])
    speed = data.get("speed")

    if not source:
        return jsonify({"error": "缺少 source 字段"}), 400
    if not segments:
        return jsonify({"error": "至少需要一个片段"}), 400

    src_path = os.path.join(UPLOAD_DIR, source)
    if not os.path.isfile(src_path):
        return jsonify({"error": f"源文件不存在: {source}"}), 404

    out_id = uuid.uuid4().hex
    out_filename = f"{out_id}.mp4"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    try:
        editor = VideoEditor(src_path)
        for seg in segments:
            start = seg.get("start", "00:00:00")
            end = seg.get("end", "00:00:05")
            editor.add_segment(start, end)
        if speed and speed != 1.0:
            editor.set_speed(speed)
        editor.export(out_path)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"output": out_filename})


@app.route("/api/files", methods=["GET"])
def list_files():
    """列出已上传的视频"""
    files = []
    for f in os.listdir(UPLOAD_DIR):
        files.append(f)
    return jsonify({"files": sorted(files)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
