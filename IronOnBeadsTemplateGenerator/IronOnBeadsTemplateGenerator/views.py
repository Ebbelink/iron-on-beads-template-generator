"""
Routes and views for the flask application.
"""

from datetime import datetime
import fileinput
from flask import render_template, request, jsonify
from werkzeug.utils import secure_filename
from IronOnBeadsTemplateGenerator import app
import os

# from PIL import Image
# import numpy
# from scipy import ndimage
from skimage import filters, img_as_ubyte, measure, feature, color, io


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
    file = getFileFromRequest(request)

    fileInfoOriginal = persistFile(file)
    imageOriginal_np = io.imread(fileInfoOriginal.path)

    imageGrayScale_np = getImageGrayscale(imageOriginal_np, fileInfoOriginal.name)

    edgeContour = getEdgeContour(imageGrayScale_np, fileInfoOriginal.name)

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
                "filename": fileInfoOriginal.name,
                "filepath": fileInfoOriginal.path,
            }
        ),
        200,
    )


def getEdgeContour(imageGrayScale, originalFileName = ""):
    edges = feature.canny(imageGrayScale, sigma=2.0, low_threshold=0.1, high_threshold=0.3)
    contours_nd = measure.find_contours(edges, 0.5)

    if originalFileName:
        upload_folder = os.path.join(app.root_path, "uploads")
        filepath = os.path.join(upload_folder, originalFileName + '-edges.png')
        io.imsave(filepath, img_as_ubyte(edges))

    return contours_nd


def getImageGrayscale(imageOriginal_np, originalFileName = ""):
    imageGrayScale = color.rgb2gray(imageOriginal_np)

    if originalFileName:
        upload_folder = os.path.join(app.root_path, "uploads")
        filepath = os.path.join(upload_folder, originalFileName + '-grayscale.png')
        io.imsave(filepath, img_as_ubyte(imageGrayScale))

    return imageGrayScale

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


def getFileFromRequest(request):
    # Check if image file is in the request
    if "image" not in request.files:
        return jsonify({"error": "No image file provided"}), 400

    file = request.files["image"]

    # Check if a file was selected
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    allowed_extensions = {"png", "jpg", "jpeg", "gif", "bmp"}
    if not (
        "." in file.filename
        and file.filename.rsplit(".", 1)[1].lower() in allowed_extensions
    ):
        return (
            jsonify(
                {"error": "Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp"}
            ),
            400,
        )
    return file
