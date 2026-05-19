"""
Unit tests for the Flask application views.
"""

from genericpath import isfile
import os.path

from _pytest.assertion.util import assertrepr_compare
import pytest
import os
import io
from typing import Final
from PIL import Image, ImageDraw
from IronOnBeadsTemplateGenerator import app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_image_car():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "images/test-image-car.jpeg"
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_bottle():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "images/test-image-bottle.jpeg"
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_pen():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images/test-image-pen-spotlight.jpeg",
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_file():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images/test-image-file-spotlight.jpeg",
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_knife():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images/test-image-knife-spotlight.jpeg",
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_safety_knife():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images/test-image-safety-knife-spotlight.jpeg",
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture
def sample_image_safety_knife_dark_bg():
    img = Image.open(
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images/test-image-safety-knife-spotlight-black-background.jpeg",
        )
    )

    # Save to bytes buffer
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="PNG")
    img_bytes.seek(0)

    return img_bytes


@pytest.fixture(autouse=True)
def run_before_and_after_tests(tmpdir):
    """Fixture to execute asserts before and after a test is run"""
    # Setup
    uploadsDir = os.path.join(app.root_path, "uploads")

    rm_dir(uploadsDir)

    yield  # Test runs here

    # Teardown


def rm_dir(path):
    if not os.path.exists(path):
        return
    else:
        if os.path.isfile(path):
            os.remove(path)
            return
        if os.path.isdir(path):
            dirContents = os.listdir(path)
            for entry in dirContents:
                rm_dir(os.path.join(path, entry))
            os.rmdir(path)
        return


class TestGenerateBeadsTemplate:
    """Test class for beads template generation."""

    CONST_ENDPOINT_PATH: Final[str] = "/generate-beads-template"

    def test_get_generate_template_page(self, client):
        """Test that the generate template page loads correctly."""
        response = client.get("/")

        assert response.status_code == 200
        assert b"Iron on beads template generator" in response.data

    def test_post_without_image(self, client):
        """Test POST request without an image file."""
        response = client.post(self.CONST_ENDPOINT_PATH)

        assert response.status_code == 400
        json_data = response.get_json()
        assert "error" in json_data
        assert "No image file provided" in json_data["error"]

    def test_post_with_empty_filename(self, client):
        """Test POST request with empty filename."""
        data = {"image": (io.BytesIO(b""), "")}
        response = client.post(
            self.CONST_ENDPOINT_PATH, data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert "error" in json_data

    def test_post_with_invalid_file_type(self, client):
        """Test POST request with invalid file type."""
        data = {"image": (io.BytesIO(b"fake pdf content"), "test.pdf")}
        response = client.post(
            self.CONST_ENDPOINT_PATH, data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 400
        json_data = response.get_json()
        assert "error" in json_data
        assert "Invalid file type" in json_data["error"]

    def test_post_with_valid_image(
        self, client, sample_image_safety_knife, sample_image_knife
    ):
        """Test POST request with a valid image file."""
        data = {"image": (sample_image_knife, "test_image.png")}
        response = client.post(
            self.CONST_ENDPOINT_PATH, data=data, content_type="multipart/form-data"
        )

        # data = {"image": (sample_image_safety_knife, "test_image.png")}
        # response = client.post(
        #     self.CONST_ENDPOINT_PATH, data=data, content_type="multipart/form-data"
        # )

        assert response.status_code == 200
        json_data = response.get_json()
        assert "filename" in json_data
        # assert "test_image.png" in json_data["filename"]

    def test_post_with_jpg_image(self, client):
        """Test POST request with a JPG image."""
        
        img = Image.new("RGB", (50, 50), color="white")
        draw = ImageDraw.Draw(img)
        draw.rectangle([(12, 12), (37, 37)], fill="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        img_bytes.seek(0)

        data = {"image": (img_bytes, "test_image.jpg")}
        response = client.post(
            self.CONST_ENDPOINT_PATH, data=data, content_type="multipart/form-data"
        )

        assert response.status_code == 200
        json_data = response.get_json()
        assert "filename" in json_data

if __name__ == "__main__":
    pytest.main([__file__, "-v"])