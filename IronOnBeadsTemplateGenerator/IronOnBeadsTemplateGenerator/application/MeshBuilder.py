"""
3D Builder module takes care of all the 3D model generation logic.
"""

import numpy as np
from shapely.geometry import Polygon, MultiPolygon
import trimesh

BASE_THICKNESS_MM = 3.0
LIP_MM = 5.0
PEG_SPACING_MM = 5.0


def build_beads_template_mesh(polygon_mm: Polygon) -> trimesh.Trimesh:
    """
    Build the full 3-D template mesh:
      - A flat base plate (polygon + 5 mm lip, 3 mm thick)
      - Pegs placed on concentric shrinking offsets of the original polygon
    """

    # Expand polygon with a lip and extrude to base thickness
    base_mesh = create_bead_plate(polygon_mm)

    # Place pegs on top of the base plate
    pegs = create_peg_layout(polygon_mm, peg_spacing_mm=PEG_SPACING_MM)

    if not pegs:
        return base_mesh

    for peg in pegs:
        peg.apply_translation([0, 0, BASE_THICKNESS_MM])

    combined = trimesh.util.concatenate([base_mesh] + pegs)
    return combined


def create_bead_plate(shape: Polygon) -> trimesh.Trimesh:
    base_polygon = shape.buffer(LIP_MM)
    # If the buffer operation results in multiple disjoint polygons, take the largest one
    if isinstance(base_polygon, MultiPolygon):
        base_polygon = max(base_polygon.geoms, key=lambda g: g.area)

    exterior_coords = np.array(base_polygon.exterior.coords)
    path2d = trimesh.path.Path2D(
        entities=[trimesh.path.entities.Line(np.arange(len(exterior_coords)))],
        vertices=exterior_coords,
    )
    base_mesh = path2d.extrude(BASE_THICKNESS_MM).to_mesh()
    return base_mesh


def create_peg_layout(bead_plate: Polygon, peg_spacing_mm=5.0) -> list:
    """
    Place pegs using concentric shrinking rings so peg rows follow the shape
    outline naturally.

    When an inward buffer splits a concave shape into multiple sub-polygons,
    all pieces are kept and processed independently.  This ensures that concave
    pockets are fully filled.
    """
    pegs = []
    placed_centres = []

    # Work queue: list of polygons still to be shrunk.
    # Seeded with the original polygon; grows when a buffer split produces
    # multiple pieces.
    pending: list[Polygon] = [bead_plate]

    while pending:
        next_pending: list[Polygon] = []

        for current_polygon in pending:
            # Walk the outer ring of this polygon piece
            tmp_ring_spacing_mm =  current_polygon.exterior.length / np.floor(current_polygon.exterior.length / peg_spacing_mm)
            _walk_ring(current_polygon.exterior, placed_centres, pegs, tmp_ring_spacing_mm)

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
            np.hypot(cx - px, cy - py) < PEG_SPACING_MM for px, py in placed_centres
        )
        if not too_close:
            placed_centres.append((cx, cy))
            pegs.append(_create_peg(cx, cy))
        distance += scan_step


def _create_peg(
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