"""LiveCap 视频剪辑 Web 服务"""

import os
import re
import uuid
import shutil

from flask import Flask, request, jsonify, send_from_directory, send_file

from agent import clip_video, concat_videos, change_speed, VideoEditor

app = Flask(__name__, static_folder="static")

UPLOAD_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "uploads"))
OUTPUT_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), "outputs"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
# 安全文件名正则：UUID hex + 扩展名
SAFE_FILENAME_RE = re.compile(r"^[a-f0-9]{32}\.[a-z0-9]+$")


def _is_safe_filename(filename: str) -> bool:
    """验证文件名是否为服务端生成的安全格式"""
    return bool(SAFE_FILENAME_RE.match(filename))


def _safe_path(base_dir: str, filename: str) -> str | None:
    """安全拼接路径，防止路径穿越"""
    if not _is_safe_filename(filename):
        return None
    full = os.path.realpath(os.path.join(base_dir, filename))
    if not full.startswith(base_dir + os.sep):
        return None
    return full


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

    ext = os.path.splitext(file.filename)[1].lower() or ".mp4"
    if ext not in ALLOWED_EXTENSIONS:
        return jsonify({"error": f"不支持的文件格式: {ext}"}), 400

    file_id = uuid.uuid4().hex
    filename = f"{file_id}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    file.save(filepath)

    return jsonify({"id": file_id, "filename": filename})


@app.route("/api/videos/<filename>")
def serve_video(filename):
    """提供视频文件访问"""
    for folder in [UPLOAD_DIR, OUTPUT_DIR]:
        path = _safe_path(folder, filename)
        if path and os.path.isfile(path):
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

    src_path = _safe_path(UPLOAD_DIR, source)
    if not src_path or not os.path.isfile(src_path):
        return jsonify({"error": "源文件不存在"}), 404

    # 验证速度参数
    if speed is not None and speed != 1.0:
        try:
            speed = float(speed)
            if speed <= 0:
                return jsonify({"error": "速度倍率必须大于0"}), 400
        except (TypeError, ValueError):
            return jsonify({"error": "速度参数无效"}), 400

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
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except RuntimeError as e:
        return jsonify({"error": "视频处理失败"}), 500

    return jsonify({"output": out_filename})


@app.route("/api/files", methods=["GET"])
def list_files():
    """列出已上传的视频"""
    files = []
    for f in os.listdir(UPLOAD_DIR):
        files.append(f)
    return jsonify({"files": sorted(files)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
