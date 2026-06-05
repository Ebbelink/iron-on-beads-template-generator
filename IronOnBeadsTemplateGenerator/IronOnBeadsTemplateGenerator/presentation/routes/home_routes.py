"""Home page routes."""

from datetime import datetime
from flask import render_template
from IronOnBeadsTemplateGenerator import app


@app.route("/")
@app.route("/generate-beads-template")
def generate_beads_template():
    """Renders the home page."""
    return render_template(
        "generate-template.html",
        title="Generate iron on beads template",
        year=datetime.now().year,
    )
