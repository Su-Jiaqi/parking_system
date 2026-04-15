from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, render_template, request
from werkzeug.utils import secure_filename

from db_utils import init_db
from parking_service import ParkingService, ParkingError

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "webp"}
MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10 MB

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

init_db()
service = ParkingService()


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index() -> str:
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


@app.route("/api/parking/upload", methods=["POST"])
def upload_parking_image() -> Any:
    if "file" not in request.files:
        return jsonify({"success": False, "message": "未检测到上传文件"}), 400

    action = request.form.get("action", "").strip().lower()
    if action not in {"entry", "exit"}:
        return jsonify({"success": False, "message": "操作类型无效，只能是 entry 或 exit"}), 400

    file = request.files["file"]
    if not file or file.filename == "":
        return jsonify({"success": False, "message": "请选择图片文件"}), 400

    if not allowed_file(file.filename):
        return jsonify({"success": False, "message": "仅支持 png/jpg/jpeg/bmp/webp 图片格式"}), 400

    filename = secure_filename(file.filename)
    save_path = UPLOAD_DIR / filename
    stem = save_path.stem
    suffix = save_path.suffix
    counter = 1
    while save_path.exists():
        save_path = UPLOAD_DIR / f"{stem}_{counter}{suffix}"
        counter += 1

    file.save(save_path)

    try:
        result: Dict[str, Any] = service.handle_request(save_path, action)
        return jsonify(result)
    except ParkingError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    except Exception as exc:  # pragma: no cover
        app.logger.exception("Unhandled error while processing parking request")
        return jsonify({"success": False, "message": f"服务器内部错误：{exc}"}), 500


@app.errorhandler(413)
def too_large(_: Exception) -> Any:
    return jsonify({"success": False, "message": "图片过大，请上传 10MB 以内的文件"}), 413


if __name__ == "__main__":
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
