"""Template generation routes."""

import os
import numpy
from flask import g, request, jsonify
from IronOnBeadsTemplateGenerator import app
from skimage import io

# Import helper functions from views (will be refactored later)
from IronOnBeadsTemplateGenerator.views import (
    SupportedThresholdMethod,
    getEdgeContour,
    getContour,
    drawPolygonOnImage,
    saveImage,
    resize_image,
    scale_polygon_to_mm,
    buildBeadsTemplateMesh,
)


@app.route("/templates/generate/outlines", methods=["POST"])
def generateTemplateOutlines():
    """Generate template outlines using multiple threshold algorithms."""
    app.logger.info(
        "Received generate-template-outlines request, request_id=%s", g.request_id
    )

    if "image" not in request.files:
        app.logger.warning("No image field in request.files")
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]
    app.logger.info(
        "File object: filename=%s, content_type=%s", file.filename, file.content_type
    )

    if file.filename == "":
        app.logger.warning("Empty filename, exit early")
        return jsonify({"error": "No file selected"}), 400

    if not (
        "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower()
        in {"png", "jpg", "jpeg", "gif", "bmp"}
    ):
        app.logger.warning("Invalid file extension. Received: %s", file.filename)
        return (
            jsonify(
                {"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp"}
            ),
            400,
        )

    imageOriginal_np = io.imread(file)
    app.logger.info(
        "Opened image: shape=%s, dtype=%s",
        imageOriginal_np.shape,
        imageOriginal_np.dtype,
    )

    # Resize image if it's too large (max dimension = 1500px)
    MAX_DIMENSION = 1500
    height, width = imageOriginal_np.shape[:2]
    max_dim = max(height, width)

    if max_dim > MAX_DIMENSION:
        app.logger.info(
            "Image exceeds max dimension (%dpx). Resizing from %dx%d",
            MAX_DIMENSION,
            width,
            height,
        )

        saveImage(
            imageOriginal_np,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "original-XXL",
        )

        imageOriginal_np = resize_image(imageOriginal_np, MAX_DIMENSION)
        app.logger.info("Resized image to: shape=%s", imageOriginal_np.shape)

    try:
        app.logger.info("Starting image processing pipeline")
        saveImage(
            imageOriginal_np,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "original",
        )

        edgeContourCustom = getEdgeContour(
            imageOriginal_np, file.filename, SupportedThresholdMethod.CUSTOM
        )
        app.logger.info("Completed CUSTOM contour detection")
        image_with_polygon = drawPolygonOnImage(
            imageOriginal_np, edgeContourCustom.polygon, color=(255, 0, 0), line_width=3
        )
        overlayCustom = saveImage(
            image_with_polygon,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "",
            "polygon_overlay_custom",
        )

        edgeContourLi = getEdgeContour(
            imageOriginal_np, file.filename, SupportedThresholdMethod.LI
        )
        app.logger.info("Completed LI contour detection")
        image_with_polygon = drawPolygonOnImage(
            imageOriginal_np, edgeContourLi.polygon, color=(255, 0, 0), line_width=3
        )
        overlayLi = saveImage(
            image_with_polygon,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "",
            "polygon_overlay_li",
        )

        edgeContourSauvola = getEdgeContour(
            imageOriginal_np, file.filename, SupportedThresholdMethod.SAUVOLA
        )
        app.logger.info("Completed SAUVOLA contour detection")
        image_with_polygon = drawPolygonOnImage(
            imageOriginal_np,
            edgeContourSauvola.polygon,
            color=(255, 0, 0),
            line_width=3,
        )
        overlaySauvola = saveImage(
            image_with_polygon,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "",
            "polygon_overlay_sauvola",
        )
        app.logger.info("Image processing complete for request_id=%s", g.request_id)
    except Exception as e:
        app.logger.exception(
            "Failed to process image for request %s: %s", g.request_id, e
        )
        return jsonify({"error": "Image processing failed"}), 500

    return (
        jsonify(
            {
                "filename": file.name,
                "xRequestId": g.request_id,
                "option1": {"algorithm": "custom", "imagePath": overlayCustom},
                "option2": {"algorithm": "li", "imagePath": overlayLi},
                "option3": {"algorithm": "sauvola", "imagePath": overlaySauvola},
            }
        ),
        200,
    )


@app.route("/templates/generate/<algorithm>", methods=["POST"])
def generateBeadsTemplatePost(algorithm):
    """Generate 3D model mesh from processed image."""
    pathToImage = ""
    # Get last image (closed gaps) and recalculate the contour
    path = f"uploads/processing/{g.request_id}"
    expected_directory = os.path.join(app.root_path, path)
    if os.path.exists(expected_directory):
        dirContents = os.listdir(expected_directory)
        for currentFileName in dirContents:
            if currentFileName.startswith(f"binary_{algorithm}-closed_gaps"):
                pathToImage = os.path.join(expected_directory, currentFileName)
                break
    if not pathToImage:
        return (
            jsonify({"error": "No processed image found for the given algorithm"}),
            400,
        )

    cleanBinaryImage = numpy.array(io.imread(pathToImage))
    contourResult = getContour(cleanBinaryImage)

    # --- Scale polygon from pixels to mm ---
    # Assume 120 DPI → 1 pixel = 25.4/120 mm
    PIXELS_PER_MM = 120 / 25.4
    polygon_mm = scale_polygon_to_mm(
        contourResult.polygon, PIXELS_PER_MM, contourResult.image_size[1]
    )

    mesh = buildBeadsTemplateMesh(polygon_mm)

    output_dir = os.path.join(app.root_path, f"uploads/processing/{g.request_id}")
    os.makedirs(output_dir, exist_ok=True)

    stl_path = os.path.join(output_dir, "beads_template.stl")
    obj_path = os.path.join(output_dir, "beads_template.obj")
    mesh.export(stl_path)
    mesh.export(obj_path)

    return jsonify(
        {
            "success": True,
            "stlPath": f"uploads/processing/{g.request_id}/beads_template.stl",
            "objPath": f"uploads/processing/{g.request_id}/beads_template.obj",
        }
    )
