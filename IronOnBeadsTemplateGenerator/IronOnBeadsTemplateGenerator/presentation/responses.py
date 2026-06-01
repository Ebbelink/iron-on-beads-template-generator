"""Response models for template generation endpoints."""

from dataclasses import dataclass, asdict
from typing import Tuple
from flask import jsonify, Response


@dataclass
class AlgorithmOptionResponse:
    """Individual algorithm option with image path."""
    algorithm: str
    imagePath: str


@dataclass
class TemplateOutlinesResponse:
    """Response for template outlines generation."""
    filename: str
    xRequestId: str
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
    stlPath: str
    objPath: str

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
