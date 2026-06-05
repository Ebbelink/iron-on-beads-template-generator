"""Response models for template generation endpoints."""

from dataclasses import dataclass, asdict
from typing import Tuple
from flask import jsonify, Response


@dataclass
class AlgorithmOptionResponse:
    """Individual algorithm option with image path."""
    algorithm: str
    image_path: str


@dataclass
class TemplateOutlinesResponse:
    """Response for template outlines generation."""
    filename: str
    x_request_id: str
    option1: AlgorithmOptionResponse
    option2: AlgorithmOptionResponse
    option3: AlgorithmOptionResponse

    def to_response(self, status_code: int = 200) -> Tuple[Response, int]:
        """Return a Flask jsonify response with status code."""
        return jsonify(asdict(self)), status_code


@dataclass
class BeadsTemplateResponse:
    """Response for 3D beads template generation."""
    success: bool
    stl_path: str
    obj_path: str

    def to_response(self, status_code: int = 200) -> Tuple[Response, int]:
        """Return a Flask jsonify response with status code."""
        return jsonify(asdict(self)), status_code


@dataclass
class ErrorResponse:
    """Error response."""
    error: str

    def to_response(self, status_code: int = 400) -> Tuple[Response, int]:
        """Return a Flask jsonify response with status code."""
        return jsonify(asdict(self)), status_code
