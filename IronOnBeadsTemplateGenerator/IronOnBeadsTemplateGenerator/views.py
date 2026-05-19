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

# from PIL import Image
# import numpy
# from scipy import ndimage
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

    getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.NIBLACK)

    getEdgeContour(imageOriginal_np, file.filename, SupportedThresholdMethod.SAUVOLA)

    
    # binary = morphology.binary_closing(binary)
    # saveImage(binary, file.name, "binary_threshold_sauvola-binary_closed")

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


def getEdgeContour(
    imageOriginal_np, filename, threshold_method=SupportedThresholdMethod.NIELS
):
    imageGrayScale_np = getImageGrayscale(imageOriginal_np, filename)
    background_value = calculateBackgroundColor(imageGrayScale_np)
    isWhiteBackground = background_value > 0.5

    threshold_method_name = threshold_method.name.lower()

    match threshold_method:
        case SupportedThresholdMethod.NIELS:
            if isWhiteBackground:
                thresholdValue = background_value * 0.9
                binary = imageGrayScale_np < thresholdValue
            else:
                thresholdValue = background_value * 1.1
                binary = imageGrayScale_np > thresholdValue
        case SupportedThresholdMethod.LI:
            thresholdValue = filters.threshold_li(imageGrayScale_np)
            # Create a binary image by applying the threshold
            if isWhiteBackground:
                binary = imageGrayScale_np < thresholdValue
            else:
                binary = imageGrayScale_np > thresholdValue
        case SupportedThresholdMethod.NIBLACK:
            thresholdValue = filters.threshold_niblack(imageGrayScale_np)
            # Create a binary image by applying the threshold
            if isWhiteBackground:
                binary = imageGrayScale_np < thresholdValue
            else:
                binary = imageGrayScale_np > thresholdValue
        case SupportedThresholdMethod.SAUVOLA:
            thresholdValue = filters.threshold_sauvola(imageGrayScale_np)
            if isWhiteBackground:
                binary = imageGrayScale_np < thresholdValue
            else:
                binary = imageGrayScale_np > thresholdValue

    saveImage(binary, filename, f"binary_threshold_{threshold_method_name}")

    # Remove noise from binary image
    binary = morphology.isotropic_closing(binary, radius=5)
    saveImage(
        binary, filename, f"binary_threshold_{threshold_method_name}-binary_closed"
    )
    binary = morphology.remove_small_objects(binary, max_size=100)
    saveImage(
        binary,
        filename,
        f"binary_threshold_{threshold_method_name}-binary_removed_small",
    )


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


def detectCannyEdges(imageGrayScale, originalFileName=""):
    edges = feature.canny(
        imageGrayScale, sigma=1.0, low_threshold=0.08, high_threshold=0.19
    )
    contours_nd = measure.find_contours(edges, 0.5)

    if originalFileName:
        upload_folder = os.path.join(app.root_path, "uploads")
        # filepath = os.path.join(upload_folder, originalFileName + "-edges-" + i.__str__() + ".png")
        filepath = os.path.join(upload_folder, originalFileName + "-edges.png")
        io.imsave(filepath, img_as_ubyte(edges))

    return contours_nd


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


class FileInfo:
    def __init__(self, filename, filepath):
        self.name = filename
        self.path = filepath


def persistFile(file):
    try:
        # Secure the filename
        filename = secure_filename(file.filename)

        # Create upload folder if it doesn't exist
        upload_folder = os.path.join(app.root_path, "uploads")
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save the file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # TODO: Process the image and generate beads template
        # Add your image processing logic here

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return FileInfo(filename, filepath)



@app.before_request
def assign_request_id():
    request_id = request.headers.get('X-REQUEST-ID') or str(uuid.uuid4())
    
    g.request_id = request_id

@app.after_request
def append_request_id(response):
    response.headers['X-REQUEST-ID'] = getattr(g, 'request_id', None)
    return response