"""Preview file serving routes."""

import os
from flask import request, jsonify, send_file
from IronOnBeadsTemplateGenerator import app


@app.route("/previews", methods=["GET"])
def getPreviews():
    """Serve preview images and generated files."""
    previewPath = request.args.get("previewPath")
    if previewPath.startswith("uploads/processing/"):
        return send_file(os.path.join(app.root_path, previewPath))
    else:
        return jsonify({"error": "Invalid preview path"}), 400
