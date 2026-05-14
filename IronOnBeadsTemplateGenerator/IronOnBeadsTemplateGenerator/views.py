"""
Routes and views for the flask application.
"""

from datetime import datetime
from flask import render_template, request, jsonify
from IronOnBeadsTemplateGenerator import app
from werkzeug.utils import secure_filename
import os

@app.route('/')
@app.route('/generate-beads-template')
def generateBeadsTemplate():
    """Renders the home page."""
    return render_template(
        'generate-template.html',
        title='Generate iron on beads template',
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

@app.route('/generate-beads-template', methods=['POST'])
def generateBeadsTemplatePost():
    """START THE MAGIC!"""

    # Check if image file is in the request
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400

    file = request.files['image']

    # Check if a file was selected
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Validate file type
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({'error': 'Invalid file type. Allowed types: png, jpg, jpeg, gif, bmp'}), 400

    try:
        # Secure the filename
        filename = secure_filename(file.filename)

        # Create upload folder if it doesn't exist
        upload_folder = os.path.join(app.root_path, 'uploads')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

        # Save the file
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # TODO: Process the image and generate beads template
        # Add your image processing logic here

        return jsonify({
            'success': True,
            'message': 'Image uploaded successfully',
            'filename': filename,
            'filepath': filepath
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
