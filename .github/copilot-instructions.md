# Iron-On Beads Template Generator - AI Agent Instructions

## Project Overview
Flask web app that converts images into 3D-printable iron-on beads templates. Users upload an image, the app extracts object contours using threshold algorithms, and generates STL/OBJ mesh files with pegs for holding beads.

## Architecture (Layered + Flask App Pattern)

### Layer Structure
```
presentation/routes/     → Flask routes (home_routes, template_routes, preview_routes)
presentation/responses.py → Dataclass-based response models (@dataclass with .to_response())
views.py                 → Middleware, helpers, core business logic (transitioning out)
application/             → Service layer (ImageHelper, MeshBuilder)
domain/                  → Domain models (SupportedThresholdMethod enum)
```

**Migration in progress**: Legacy code in `views.py` is gradually moving to proper layers. New code goes in `application/` or `domain/`.

### Request Flow
1. **Upload** → `/templates/generate/outlines` (POST with image file)
2. **Process** → Runs 3 threshold algorithms (CUSTOM, LI, SAUVOLA), returns overlay images
3. **Select** → User picks best contour detection result
4. **Generate** → `/templates/generate/<algorithm>` creates 3D mesh from selected algorithm's binary image
5. **Download** → Returns STL and OBJ file paths

### Request ID System
- `@app.before_request` assigns UUID to `g.request_id` (or reuses `X-REQUEST-ID` header)
- All processing artifacts stored in `uploads/processing/{request_id}/`
- Enables stateless request tracking across image processing pipeline steps

## Key Technologies & Patterns

### Image Processing Pipeline (ImageHelper.py)
```python
grayscale → threshold (custom/li/sauvola) → remove_small_objects → isotropic_closing → contour detection
```
- **Background detection**: Uses edge pixels to determine if white/black background, inverts threshold logic accordingly
- **Multiple thresholds**: Always generate 3 options (CUSTOM adapts to background, LI/SAUVOLA are scikit-image algorithms)
- **Morphology cleanup**: `remove_small_objects(max_size=130)` + `isotropic_closing(radius=5)` removes noise

### 3D Mesh Generation (MeshBuilder.py)
- **Concentric ring peg placement**: Shrinks polygon inward by `PEG_SPACING_MM` (5mm) per iteration
- **Handles splits**: When `buffer(-spacing)` creates MultiPolygon (concave shapes), processes ALL pieces independently
- **Coordinate systems**: Pixels → millimeters conversion uses `PIXELS_PER_MM = 120/25.4`
- **Y-axis flip**: `scale_polygon_to_mm()` inverts Y (`image_height - y`) to match 3D orientation with image
- **Peg spacing adjustment**: Each ring recalculates spacing as `ring.length / floor(ring.length / peg_spacing)` to distribute pegs evenly
- **Visualization**: Set `visualize_rings=True` in `build_beads_template_mesh()` to generate ring layout PNG using Pillow

### Dependencies (requirements.txt)
- **Azure telemetry**: OpenTelemetry enabled when `APPLICATIONINSIGHTS_CONNECTION_STRING` env var set
- ALWAYS look at `requirements.txt` if there already is a dependency that can tackle the problem before starting work, especially for image processing or Azure SDKs

## Development Workflows

### Running Locally
```bash
# Development server (uses runserver.py)
python IronOnBeadsTemplateGenerator/runserver.py
# Defaults: localhost:5555, set FLASK_DEBUG=True for debug mode

# Production container
docker build . -t iron-on-beads
docker run -p 8000:8000 iron-on-beads
```

### Testing
```bash
# Run pytest (Visual Studio or CLI)
pytest IronOnBeadsTemplateGenerator/tests/
```
- **Test fixtures**: `sample_image_car`, `sample_image_bottle` in `test_generate_template_outlines.py`
- **Test images**: Located in `IronOnBeadsTemplateGenerator/tests/images/`
- **Docker build runs tests**: Dockerfile includes `pytest` step before runtime stage

### Deployment (Azure Container Apps)
- **IaC**: `infra.bicep` defines Container App + Log Analytics + App Insights
- **Persistent storage**: `/home/uploads` used (Azure mounts persistent storage to `/home`)
- **Gunicorn config**: 2 workers, 120s timeout (mesh generation is slow), non-root user `appuser`

## Project-Specific Conventions

### Response Pattern
All API responses use dataclasses with `.to_response(status_code)`:
```python
@dataclass
class ErrorResponse:
    error: str
    def to_response(self, status_code: int = 400) -> Tuple[Response, int]:
        return jsonify(asdict(self)), status_code
```

### File Saving Pattern
```python
save_image(array, filename, f"uploads/processing/{g.request_id}", prefix, suffix)
# Creates: uploads/processing/{uuid}/{prefix}-{suffix}-{filename}.png
```

### Shapely Polygon Validation
Always validate/heal polygons after `find_contours()`:
```python
if not polygon.is_valid:
    polygon = make_valid(polygon)
if isinstance(polygon, MultiPolygon):
    polygon = max(polygon.geoms, key=lambda g: g.area)  # Keep largest
```

### Logging
- Use `app.logger.info/warning/exception` (configured in `__init__.py`)
- Include `request_id` in logs: `app.logger.info("..., request_id=%s", g.request_id)`
- Internal telemetry logs filtered below ERROR level (see `_ExcludeInternalLogsFilter`)

## Critical Details

### Mesh Constants (MeshBuilder.py)
```python
BASE_THICKNESS_MM = 3.0   # Base plate height
LIP_MM = 5.0              # Extra margin around shape
PEG_SPACING_MM = 5.0      # Distance between peg centers
```
**Do not change** without understanding iron-on bead physical constraints.

### File Extension Validation
Only accept: `png, jpg, jpeg, gif, bmp` (see `template_routes.py`)

### Image Size Limit
Max dimension: 1500px (auto-resized in `/templates/generate/outlines`)

### Pixel → MM Conversion
Assumes 120 DPI images: `1 pixel = 25.4/120 mm ≈ 0.212 mm`

## Common Pitfalls

1. **Don't add new image processing steps without saving intermediate results** – debugging relies on saved artifacts
2. **MultiPolygon handling**: After `buffer()` operations, always check if result is MultiPolygon (especially after negative buffers on concave shapes)
3. **Coordinate system confusion**: Shapely uses (x, y), numpy arrays are (row, col) = (y, x)
4. **Flask g object scope**: `g.request_id` only available during request context
5. **Test images are fixtures**: Don't hardcode paths, use `@pytest.fixture` functions

## When Adding Features

- **New threshold algorithm**: Add to `SupportedThresholdMethod` enum, handle in `get_clean_binary_image()` match statement
- **New mesh parameter**: Add to `build_beads_template_mesh()` signature, pass through to `create_peg_layout()`
- **New route**: Create in `presentation/routes/`, import in `__init__.py`
- **New response type**: Add dataclass to `presentation/responses.py` with `.to_response()` method
