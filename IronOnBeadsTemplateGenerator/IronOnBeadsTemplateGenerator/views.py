"""
Helper functions and business logic for the flask application.
Note: Routes have been moved to presentation/routes/
"""

from datetime import datetime
from http.client import OK
from uuid import UUID
import uuid
from flask import g, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from IronOnBeadsTemplateGenerator import app
import os
import numpy
from enum import Enum
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from PIL import Image, ImageDraw
from skimage import filters, img_as_ubyte, measure, feature, color, io, morphology, transform
import trimesh
import trimesh.creation
import numpy as np



class SupportedThresholdMethod(Enum):
    CUSTOM = 1
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
    imageOriginal_np, filename, threshold_method=SupportedThresholdMethod.CUSTOM
) -> EdgeContourResult:
    imageGrayScale_np = getImageGrayscale(imageOriginal_np, filename)
    saveImage(
        imageGrayScale_np, filename, f"uploads/processing/{g.request_id}", "grayscale"
    )

    cleanBinaryImage = getCleanBinaryImage(
        imageGrayScale_np, threshold_method, filename
    )

    return getContour(cleanBinaryImage)


def getContour(cleanedBinaryImage):
    height, width = cleanedBinaryImage.shape
    contours = measure.find_contours(cleanedBinaryImage, level=0.5)
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

    return EdgeContourResult(polygon, centroid, (width, height))


def getCleanBinaryImage(imageGrayScale_np, threshold_method, filename):
    background_value = calculateBackgroundColor(imageGrayScale_np)
    isWhiteBackground = background_value > 0.5
    # height, width = imageGrayScale_np.shape

    imageToThreshold = imageGrayScale_np

    match threshold_method:
        case SupportedThresholdMethod.CUSTOM:
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
    saveImage(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}",
    )

    # Remove noise from binary image
    binary = morphology.remove_small_objects(binary, max_size=130)
    saveImage(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}-removed_small_objects",
    )

    binary = morphology.isotropic_closing(binary, radius=5)
    saveImage(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}-closed_gaps",
    )

    return binary


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


def saveImage(image, filename, directory="uploads", prefix="", postfix="") -> str:
    upload_folder = os.path.join(app.root_path, f"{directory}")
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder)

    constructed_filename = (
        (prefix + "-" if prefix else "")
        + filename
        + ("-" + postfix if postfix else "")
        + ".png"
    )
    filepath = os.path.join(upload_folder, constructed_filename)
    io.imsave(filepath, img_as_ubyte(image))

    return os.path.join(directory, constructed_filename)


def getImageGrayscale(imageOriginal_np, originalFileName=""):
    # Strip alpha channel if present (e.g. PNG with transparency) rgb2gray expects 3 channels (RGB); RGBA will cause a dimension mismatch
    if imageOriginal_np.ndim == 3 and imageOriginal_np.shape[2] == 4:
        imageOriginal_np = imageOriginal_np[:, :, :3]

    imageGrayScale = color.rgb2gray(imageOriginal_np)

    if originalFileName:
        saveImage(
            img_as_ubyte(imageGrayScale),
            originalFileName,
            f"uploads/processing/{g.request_id}",
            "",
            "-grayscale.png",
        )

    return imageGrayScale


def resize_image(image_np, max_dimension=1400):
    """
    Resize an image so that its largest dimension doesn't exceed max_dimension.
    Maintains aspect ratio.

    Parameters:
    - image_np: numpy array of the image
    - max_dimension: maximum allowed dimension in pixels (default: 1400)

    Returns:
    - resized image as numpy array
    """
    height, width = image_np.shape[:2]
    max_dim = max(height, width)

    if max_dim <= max_dimension:
        return image_np

    # Calculate new dimensions maintaining aspect ratio
    scale_factor = max_dimension / max_dim
    new_height = int(height * scale_factor)
    new_width = int(width * scale_factor)

    resized = transform.resize(
        image_np,
        (new_height, new_width),
        anti_aliasing=True,
        preserve_range=True
    )

    return resized.astype(image_np.dtype)


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


def scale_polygon_to_mm(
    polygon: Polygon, pixels_per_mm: float, image_height_px: int = None
) -> Polygon:
    """Scale a pixel-space Shapely polygon to millimetres.

    Flips the Y axis when image_height_px is provided so that the 3D model
    orientation matches the original image (pixel Y increases downward,
    3D Y increases upward).
    """
    if image_height_px is not None:
        coords = [
            (x / pixels_per_mm, (image_height_px - y) / pixels_per_mm)
            for x, y in polygon.exterior.coords
        ]
    else:
        coords = [
            (x / pixels_per_mm, y / pixels_per_mm) for x, y in polygon.exterior.coords
        ]
    return Polygon(coords)


def create_peg(
    x: float, y: float, base_radius=1.25, top_radius=0.75, height=3.5, sections=16
) -> trimesh.Trimesh:
    """Create a single peg at position (x, y) sitting on z=0.

    Built from a cylinder with the top cap vertices scaled inward so the peg
    tapers from base_radius at the bottom to top_radius at the top.
    """
    peg = trimesh.creation.cylinder(
        radius=base_radius, height=height, sections=sections
    )

    vertices = peg.vertices.copy()
    top_z = vertices[:, 2].max()
    top_mask = np.isclose(vertices[:, 2], top_z)

    # Scale top cap XY from base_radius → top_radius
    vertices[top_mask, :2] *= top_radius / base_radius

    peg = trimesh.Trimesh(vertices=vertices, faces=peg.faces.copy(), process=False)
    peg.apply_translation([x, y, 0])
    return peg


def _walk_ring(ring, placed_centres: list, pegs: list, peg_spacing_mm: float):
    """Walk a single ring and place pegs where spacing allows."""
    ring_length = ring.length
    if ring_length < peg_spacing_mm:
        return

    scan_step = peg_spacing_mm / 10.0
    distance = 0.0
    while distance < ring_length:
        pt = ring.interpolate(distance)
        cx, cy = pt.x, pt.y

        too_close = any(
            np.hypot(cx - px, cy - py) < peg_spacing_mm for px, py in placed_centres
        )
        if not too_close:
            placed_centres.append((cx, cy))
            pegs.append(create_peg(cx, cy))
        distance += scan_step


def place_pegs_on_polygon(polygon: Polygon, peg_spacing_mm=5.0) -> list:
    """
    Place pegs using concentric shrinking rings so peg rows follow the shape
    outline naturally.

    When an inward buffer splits a concave shape into multiple sub-polygons,
    all pieces are kept and processed independently.  This ensures that concave
    pockets — which would previously be silently discarded by keeping only the
    largest piece — are fully filled.
    """
    pegs = []
    placed_centres = []

    # Work queue: list of polygons still to be shrunk.
    # Seeded with the original polygon; grows when a buffer split produces
    # multiple pieces.
    pending: list[Polygon] = [polygon]

    while pending:
        next_pending: list[Polygon] = []

        for current_polygon in pending:
            # Walk the outer ring of this polygon piece
            _walk_ring(current_polygon.exterior, placed_centres, pegs, peg_spacing_mm)

            # Shrink inward by one full peg spacing
            shrunk = current_polygon.buffer(-peg_spacing_mm)
            if shrunk.is_empty:
                continue

            # If the shrink split the polygon, keep ALL pieces for the next
            # iteration rather than discarding the smaller ones.
            if isinstance(shrunk, MultiPolygon):
                next_pending.extend(shrunk.geoms)
            else:
                next_pending.append(shrunk)

        pending = next_pending

    return pegs


def buildBeadsTemplateMesh(polygon_mm: Polygon) -> trimesh.Trimesh:
    """
    Build the full 3-D template mesh:
      - A flat base plate (polygon + 5 mm lip, 3 mm thick)
      - Pegs placed on concentric shrinking offsets of the original polygon
    """
    BASE_THICKNESS_MM = 3.0
    LIP_MM = 5.0
    PEG_SPACING_MM = 5.0

    # Expand polygon with a lip and extrude to base thickness
    base_polygon = polygon_mm.buffer(LIP_MM)
    if isinstance(base_polygon, MultiPolygon):
        base_polygon = max(base_polygon.geoms, key=lambda g: g.area)

    exterior_coords = np.array(base_polygon.exterior.coords)
    path2d = trimesh.path.Path2D(
        entities=[trimesh.path.entities.Line(np.arange(len(exterior_coords)))],
        vertices=exterior_coords,
    )
    base_mesh = path2d.extrude(BASE_THICKNESS_MM).to_mesh()

    # Place pegs on top of the base plate
    pegs = place_pegs_on_polygon(polygon_mm, peg_spacing_mm=PEG_SPACING_MM)

    if not pegs:
        return base_mesh

    for peg in pegs:
        peg.apply_translation([0, 0, BASE_THICKNESS_MM])

    combined = trimesh.util.concatenate([base_mesh] + pegs)
    return combined


@app.before_request
def assign_request_id():
    request_id = request.headers.get("X-REQUEST-ID") or str(uuid.uuid4())

    g.request_id = request_id


@app.after_request
def append_request_id(response):
    response.headers["X-REQUEST-ID"] = getattr(g, "request_id", None)
    return response