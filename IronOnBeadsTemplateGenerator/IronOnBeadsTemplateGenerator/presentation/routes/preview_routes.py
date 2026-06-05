"""Preview file serving routes."""

import os
from flask import request, jsonify, send_file
from IronOnBeadsTemplateGenerator import app


@app.route("/previews", methods=["GET"])
def get_previews():
    """Serve preview images and generated files."""
    preview_path = request.args.get("preview_path")
    if preview_path.startswith("uploads/processing/"):
        return send_file(os.path.join(app.root_path, preview_path))
    else:
        return jsonify({"error": "Invalid preview path"}), 400
