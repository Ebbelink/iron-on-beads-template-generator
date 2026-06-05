"""Template generation routes."""

import os
import numpy
from flask import g, request
from IronOnBeadsTemplateGenerator import app
from skimage import io

from IronOnBeadsTemplateGenerator.presentation.responses import (
    TemplateOutlinesResponse,
    AlgorithmOptionResponse,
    BeadsTemplateResponse,
    ErrorResponse,
)

# Import helper functions from views (will be refactored later)
from IronOnBeadsTemplateGenerator.views import (
    SupportedThresholdMethod,
    get_edge_contour,
    get_contour,
    scale_polygon_to_mm,
)

from IronOnBeadsTemplateGenerator.application.ImageHelper import (
    save_image,
    resize_image,
    draw_polygon
)

from IronOnBeadsTemplateGenerator.application.MeshBuilder import build_beads_template_mesh


@app.route("/templates/generate/outlines", methods=["POST"])
def generate_template_outlines():
    """Generate template outlines using multiple threshold algorithms."""
    app.logger.info(
        "Received generate-template-outlines request, request_id=%s", g.request_id
    )

    if "image" not in request.files:
        app.logger.warning("No image field in request.files")
        return ErrorResponse("No image file provided").to_response(400)

    file = request.files["image"]
    app.logger.info(
        "File object: filename=%s, content_type=%s", file.filename, file.content_type
    )

    if file.filename == "":
        app.logger.warning("Empty filename, exit early")
        return ErrorResponse("No file selected").to_response(400)

    if not (
        "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower()
        in {"png", "jpg", "jpeg", "gif", "bmp"}
    ):
        app.logger.warning("Invalid file extension. Received: %s", file.filename)
        return ErrorResponse("Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp").to_response(400)

    image_original_np = io.imread(file)
    app.logger.info(
        "Opened image: shape=%s, dtype=%s",
        image_original_np.shape,
        image_original_np.dtype,
    )

    # Resize image if it's too large (max dimension = 1500px)
    MAX_DIMENSION = 1500
    height, width = image_original_np.shape[:2]
    max_dim = max(height, width)

    if max_dim > MAX_DIMENSION:
        app.logger.info(
            "Image exceeds max dimension (%dpx). Resizing from %dx%d",
            MAX_DIMENSION,
            width,
            height,
        )

        save_image(
            image_original_np,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "original-XXL",
        )

        image_original_np = resize_image(image_original_np, MAX_DIMENSION)
        app.logger.info("Resized image to: shape=%s", image_original_np.shape)

    try:
        app.logger.info("Starting image processing pipeline")
        save_image(
            image_original_np,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "original",
        )

        edge_contour_custom = get_edge_contour(
            image_original_np, file.filename, SupportedThresholdMethod.CUSTOM
        )
        app.logger.info("Completed CUSTOM contour detection")
        image_with_polygon = draw_polygon(
            image_original_np, edge_contour_custom.polygon, color=(255, 0, 0), line_width=3
        )
        overlay_custom = save_image(
            image_with_polygon,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "",
            "polygon_overlay_custom",
        )

        edge_contour_li = get_edge_contour(
            image_original_np, file.filename, SupportedThresholdMethod.LI
        )
        app.logger.info("Completed LI contour detection")
        image_with_polygon = draw_polygon(
            image_original_np, edge_contour_li.polygon, color=(255, 0, 0), line_width=3
        )
        overlay_li = save_image(
            image_with_polygon,
            file.filename,
            f"uploads/processing/{g.request_id}",
            "",
            "polygon_overlay_li",
        )

        edge_contour_sauvola = get_edge_contour(
            image_original_np, file.filename, SupportedThresholdMethod.SAUVOLA
        )
        app.logger.info("Completed SAUVOLA contour detection")
        image_with_polygon = draw_polygon(
            image_original_np,
            edge_contour_sauvola.polygon,
            color=(255, 0, 0),
            line_width=3,
        )
        overlay_sauvola = save_image(
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
        return ErrorResponse("Image processing failed").to_response(500)

    response = TemplateOutlinesResponse(
        filename=file.name,
        x_request_id=g.request_id,
        option1=AlgorithmOptionResponse(algorithm="custom", image_path=overlay_custom),
        option2=AlgorithmOptionResponse(algorithm="li", image_path=overlay_li),
        option3=AlgorithmOptionResponse(algorithm="sauvola", image_path=overlay_sauvola),
    )

    return response.to_response()


@app.route("/templates/generate/<algorithm>", methods=["POST"])
def generate_beads_template_post(algorithm):
    """Generate 3D model mesh from processed image."""
    path_to_image = ""
    # Get last image (closed gaps) and recalculate the contour
    path = f"uploads/processing/{g.request_id}"
    expected_directory = os.path.join(app.root_path, path)
    if os.path.exists(expected_directory):
        dir_contents = os.listdir(expected_directory)
        for current_filename in dir_contents:
            if current_filename.startswith(f"binary_{algorithm}-closed_gaps"):
                path_to_image = os.path.join(expected_directory, current_filename)
                break
    if not path_to_image:
        return ErrorResponse("No processed image found for the given algorithm").to_response(400)

    clean_binary_image = numpy.array(io.imread(path_to_image))
    contour_result = get_contour(clean_binary_image)

    # --- Scale polygon from pixels to mm ---
    # Assume 120 DPI → 1 pixel = 25.4/120 mm
    PIXELS_PER_MM = 120 / 25.4
    polygon_mm = scale_polygon_to_mm(
        contour_result.polygon, PIXELS_PER_MM, contour_result.image_size[1]
    )

    mesh = build_beads_template_mesh(polygon_mm)

    output_dir = os.path.join(app.root_path, f"uploads/processing/{g.request_id}")
    os.makedirs(output_dir, exist_ok=True)

    stl_path = os.path.join(output_dir, "beads_template.stl")
    obj_path = os.path.join(output_dir, "beads_template.obj")
    mesh.export(stl_path)
    mesh.export(obj_path)

    response = BeadsTemplateResponse(
        success=True,
        stl_path=f"uploads/processing/{g.request_id}/beads_template.stl",
        obj_path=f"uploads/processing/{g.request_id}/beads_template.obj",
    )

    return response.to_response()
