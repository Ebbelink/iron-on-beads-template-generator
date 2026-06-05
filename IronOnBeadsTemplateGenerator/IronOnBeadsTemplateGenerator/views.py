"""
Helper functions and business logic for the flask application.
Note: Routes have been moved to presentation/routes/
"""

import uuid
from flask import g, request
from IronOnBeadsTemplateGenerator import app
from shapely.geometry import Polygon, MultiPolygon
from shapely.validation import make_valid
from skimage import measure

from IronOnBeadsTemplateGenerator.domain.models import SupportedThresholdMethod
from IronOnBeadsTemplateGenerator.application.ImageHelper import (
    get_image_grayscale,
    save_image,
    get_clean_binary_image
)


class EdgeContourResult:
    def __init__(self, polygon, centroid, image_size):
        self.polygon = polygon
        self.centroid = centroid
        self.image_size = image_size

    polygon: Polygon | MultiPolygon
    centroid: tuple[float, float]
    image_size: tuple[int, int]


def get_edge_contour(
    image_original_np, filename, threshold_method=SupportedThresholdMethod.CUSTOM
) -> EdgeContourResult:
    image_grayscale_np = get_image_grayscale(image_original_np, filename)
    save_image(
        image_grayscale_np, filename, f"uploads/processing/{g.request_id}", "grayscale"
    )

    clean_binary_image = get_clean_binary_image(
        image_grayscale_np, threshold_method, filename
    )

    return get_contour(clean_binary_image)


def get_contour(cleaned_binary_image):
    height, width = cleaned_binary_image.shape
    contours = measure.find_contours(cleaned_binary_image, level=0.5)
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



@app.before_request
def assign_request_id():
    request_id = request.headers.get("X-REQUEST-ID") or str(uuid.uuid4())

    g.request_id = request_id


@app.after_request
def append_request_id(response):
    response.headers["X-REQUEST-ID"] = getattr(g, "request_id", None)
    return response