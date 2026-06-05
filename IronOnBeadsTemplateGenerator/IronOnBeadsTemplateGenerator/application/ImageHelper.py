"""
Helper for image manipulation
"""

import os
from flask import g
from IronOnBeadsTemplateGenerator import app
from PIL import Image, ImageDraw
import numpy
from skimage import filters, img_as_ubyte, measure, feature, color, io, morphology, transform
from IronOnBeadsTemplateGenerator.domain.models import SupportedThresholdMethod


def get_clean_binary_image(image_grayscale_np, threshold_method, filename):
    background_value = calculate_background_color(image_grayscale_np)
    is_white_background = background_value > 0.5
    # height, width = image_grayscale_np.shape

    image_to_threshold = image_grayscale_np

    match threshold_method:
        case SupportedThresholdMethod.CUSTOM:
            if is_white_background:
                threshold_value = background_value * 0.8
                binary = image_to_threshold < threshold_value
            else:
                threshold_value = background_value * 1.1
                binary = image_to_threshold > threshold_value
        case SupportedThresholdMethod.LI:
            threshold_value = filters.threshold_li(image_to_threshold)
            if is_white_background:
                binary = image_to_threshold < threshold_value
            else:
                binary = image_to_threshold > threshold_value
        case SupportedThresholdMethod.NIBLACK:
            threshold_value = filters.threshold_niblack(image_to_threshold, 29)
            if is_white_background:
                binary = image_to_threshold < threshold_value
            else:
                binary = image_to_threshold > threshold_value
        case SupportedThresholdMethod.SAUVOLA:
            threshold_value = filters.threshold_sauvola(image_to_threshold)
            if is_white_background:
                binary = image_to_threshold < threshold_value
            else:
                binary = image_to_threshold > threshold_value

    threshold_method_name = threshold_method.name.lower()
    save_image(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}",
    )

    # Remove noise from binary image
    binary = morphology.remove_small_objects(binary, max_size=130)
    save_image(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}-removed_small_objects",
    )

    binary = morphology.isotropic_closing(binary, radius=5)
    save_image(
        binary,
        filename,
        f"uploads/processing/{g.request_id}",
        f"binary_{threshold_method_name}-closed_gaps",
    )

    return binary


def draw_polygon(image_np, polygon, color=(255, 0, 0), line_width=2):
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


def save_image(image, filename, directory="uploads", prefix="", postfix="") -> str:
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


def get_image_grayscale(image_original_np, original_filename=""):
    # Strip alpha channel if present (e.g. PNG with transparency) rgb2gray expects 3 channels (RGB); RGBA will cause a dimension mismatch
    if image_original_np.ndim == 3 and image_original_np.shape[2] == 4:
        image_original_np = image_original_np[:, :, :3]

    image_grayscale = color.rgb2gray(image_original_np)

    if original_filename:
        save_image(
            img_as_ubyte(image_grayscale),
            original_filename,
            f"uploads/processing/{g.request_id}",
            "",
            "-grayscale.png",
        )

    return image_grayscale


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

def calculate_background_color(image_np, corner_size=20):
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