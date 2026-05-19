"""
Routes and views for the flask application.
"""

from datetime import datetime
from uuid import UUID
import uuid
from flask import g, render_template, request, jsonify
from werkzeug.utils import secure_filename
from IronOnBeadsTemplateGenerator import app
import os
import numpy
from enum import Enum
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from PIL import Image, ImageDraw
from skimage import filters, img_as_ubyte, measure, feature, color, io, morphology


@app.route("/")
@app.route("/generate-beads-template")
def generateBeadsTemplate():
    """Renders the home page."""
    return render_template(
        "generate-template.html",
        title="Generate iron on beads template",
        year=datetime.now().year,
    )


# @app.route('/contact')
# def contact():
#     """Renders the contact page."""
#     return render_template(
#         'contact.html',
#         title='Contact',
#         year=datetime.now().year,
#         message='Your contact page.'
#     )

# @app.route('/about')
# def about():
#     """Renders the about page."""
#     return render_template(
#         'about.html',
#         title='About',
#         year=datetime.now().year,
#         message='Your application description page.'
#     )


@app.route("/generate-beads-template", methods=["POST"])
def generateBeadsTemplatePost():
    """START THE MAGIC!"""
    pegBeadRadiusInMm = 5

    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    if not (
        "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower()
        in {"png", "jpg", "jpeg", "gif", "bmp"}
    ):
        return (
            jsonify(
                {"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp"}
            ),
            400,
        )

    # fileInfoOriginal = persistFile(file)
    imageOriginal_np = io.imread(file)
    saveImage(imageOriginal_np, file.filename, "original")

    getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.NIELS)

    getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.LI)

    # getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.NIBLACK)

    getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.SAUVOLA)

    # edgeContour_nd = getEdgeContour(imageGrayScale_np, file.name)

    # deNoised = morphology.remove_small_objects(edgeContour_nd, 100)

    # contourVector = buildContourVector(edgeContour)

    # Start building the 3D model

    # create a flat shape the size of the contour vector + [pegBeadRadiusInMm]mm
    # Determine center of the contour vector. This will be the center for all transformations
    # DO
    # place pegs on the contour vector
    #   Determine length of contour vector. Modulo 5mm to determine how many pegs can fit on the contour vector
    #   Start placing pegs on the contour vector every ~[pegBeadRadiusInMm]mm.
    #     If the TO BE PLACED peg is within [pegBeadRadiusInMm]mm of an already placed peg SKIP IT
    #   Resize contour vector -[pegBeadRadiusInMm]mm around center
    # WHILE contour vector is larger than [pegBeadRadiusInMm]mm

    # DONE BUILDING MODEL

    # exportModelToObj(3dModel)

    return (
        jsonify(
            {
                "filename": file.name,
                # "filepath": fileInfoOriginal.path,
            }
        ),
        200,
    )


class SupportedThresholdMethod(Enum):
    NIELS = 1
    LI = 2
    NIBLACK = 3
    SAUVOLA = 4


class EdgeContourResult:
    def __init__(self, polygon, centroid, image_size):
        self.polygon = polygon
        self.centroid = centroid
        self.image_size = image_size

    polygon: Polygon | MultiPolygon
    centroid: tuple[float, float]
    image_size: tuple[int, int]


def getEdgeContour(
    imageOriginal_np, filename, threshold_method=SupportedThresholdMethod.NIELS
) -> EdgeContourResult:
    imageGrayScale_np = getImageGrayscale(imageOriginal_np, filename)
    saveImage(imageGrayScale_np, filename, "grayscale")

    background_value = calculateBackgroundColor(imageGrayScale_np)
    isWhiteBackground = background_value > 0.5
    height, width = imageGrayScale_np.shape

    imageToThreshold = imageGrayScale_np

    match threshold_method:
        case SupportedThresholdMethod.NIELS:
            if isWhiteBackground:
                thresholdValue = background_value * 0.8
                binary = imageToThreshold < thresholdValue
            else:
                thresholdValue = background_value * 1.1
                binary = imageToThreshold > thresholdValue
        case SupportedThresholdMethod.LI:
            thresholdValue = filters.threshold_li(imageToThreshold)
            if isWhiteBackground:
                binary = imageToThreshold < thresholdValue
            else:
                binary = imageToThreshold > thresholdValue
        case SupportedThresholdMethod.NIBLACK:
            thresholdValue = filters.threshold_niblack(imageToThreshold, 29)
            if isWhiteBackground:
                binary = imageToThreshold < thresholdValue
            else:
                binary = imageToThreshold > thresholdValue
        case SupportedThresholdMethod.SAUVOLA:
            thresholdValue = filters.threshold_sauvola(imageToThreshold)
            if isWhiteBackground:
                binary = imageToThreshold < thresholdValue
            else:
                binary = imageToThreshold > thresholdValue

    threshold_method_name = threshold_method.name.lower()
    saveImage(binary, filename, f"binary_threshold_{threshold_method_name}")

    # Remove noise from binary image
    binary = morphology.remove_small_objects(binary, max_size=130)
    saveImage(
        binary,
        filename,
        f"binary_threshold_{threshold_method_name}-binary_removed_small",
    )

    binary = morphology.isotropic_closing(binary, radius=5)
    saveImage(
        binary, filename, f"binary_threshold_{threshold_method_name}-binary_closed"
    )

    contours = measure.find_contours(binary, level=0.5)
    largest_contour = max(contours, key=len)

    # ------------------------------------------------------------------ #
    # 6. Convert to Shapely Polygon                                      #
    # ------------------------------------------------------------------ #
    # find_contours returns (row, col) → convert to (x, y) = (col, row)
    xy_points = [(pt[1], pt[0]) for pt in largest_contour]

    polygon = Polygon(xy_points)

    # Heal any self-intersections from pixel-level noise
    if not polygon.is_valid:
        polygon = make_valid(polygon)

    # If make_valid split it into a MultiPolygon, keep only the largest part
    if isinstance(polygon, MultiPolygon):
        polygon = max(polygon.geoms, key=lambda g: g.area)

    # Lightly smooth the polygon to reduce pixel staircase artifacts
    polygon = polygon.simplify(tolerance=1.0, preserve_topology=True)

    # ------------------------------------------------------------------ #
    # 7. Compute centroid and scale                                      #
    # ------------------------------------------------------------------ #
    centroid = (polygon.centroid.x, polygon.centroid.y)

    # Draw polygon on grayscale image
    image_with_polygon = drawPolygonOnImage(
        imageGrayScale_np, polygon, color=(255, 0, 0), line_width=3
    )
    saveImage(
        image_with_polygon, filename, "", f"polygon_overlay_{threshold_method_name}"
    )

    return EdgeContourResult(polygon, centroid, (width, height))


def drawPolygonOnImage(image_np, polygon, color=(255, 0, 0), line_width=2):
    """
    Draw a Shapely polygon on a numpy image array.

    Args:
        image_np: grayscale numpy array (height, width)
        polygon: Shapely Polygon object
        color: RGB tuple (default: bright red)
        line_width: thickness of the polygon outline

    Returns:
        RGB numpy array with polygon drawn
    """
    if len(image_np.shape) == 2:
        image_rgb = numpy.stack([image_np, image_np, image_np], axis=2)
    else:
        image_rgb = image_np.copy()

    if image_rgb.dtype != numpy.uint8:
        image_rgb = img_as_ubyte(image_rgb)

    pil_image = Image.fromarray(image_rgb)
    draw = ImageDraw.Draw(pil_image)

    # Extract polygon exterior coordinates
    coords = list(polygon.exterior.coords)

    # Draw the polygon
    draw.polygon(coords, outline=color, width=line_width)

    # Convert back to numpy
    return numpy.array(pil_image)


def saveImage(image, filename, prefix="", postfix=""):
    upload_folder = os.path.join(app.root_path, f"uploads/{g.request_id}")
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    filepath = os.path.join(
        upload_folder,
        (prefix + "-" if prefix else "")
        + filename
        + (postfix + "-" if postfix else "")
        + ".png",
    )
    io.imsave(filepath, img_as_ubyte(image))


def getImageGrayscale(imageOriginal_np, originalFileName=""):
    imageGrayScale = color.rgb2gray(imageOriginal_np)

    if originalFileName:
        upload_folder = os.path.join(app.root_path, "uploads")
        filepath = os.path.join(upload_folder, originalFileName + "-grayscale.png")
        io.imsave(filepath, img_as_ubyte(imageGrayScale))

    return imageGrayScale


def calculateBackgroundColor(image_np, corner_size=20):
    """
    Calculate background color by sampling the four corners of the image.

    Parameters:
    - image_np: numpy array of the image
    - corner_size: size of the corner region to sample (default: 20x20 pixels)

    Returns:
    - background_color: mean color value of corners
    """
    h, w = image_np.shape[:2]
    corner_size = min(corner_size, h // 4, w // 4)

    top_left = image_np[:corner_size, :corner_size]
    top_right = image_np[:corner_size, -corner_size:]
    bottom_left = image_np[-corner_size:, :corner_size]
    bottom_right = image_np[-corner_size:, -corner_size:]

    corners = numpy.concatenate(
        [
            top_left.flatten(),
            top_right.flatten(),
            bottom_left.flatten(),
            bottom_right.flatten(),
        ]
    )

    # Calculate median (more robust than mean for outliers)
    background_color = numpy.median(corners)

    return background_color


@app.before_request
def assign_request_id():
    request_id = request.headers.get("X-REQUEST-ID") or str(uuid.uuid4())

    g.request_id = request_id


@app.after_request
def append_request_id(response):
    response.headers["X-REQUEST-ID"] = getattr(g, "request_id", None)
    return response