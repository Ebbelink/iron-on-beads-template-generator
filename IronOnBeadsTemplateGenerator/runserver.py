"""
This script runs the IronOnBeadsTemplateGenerator application using a development server.
"""

from os import environ
from IronOnBeadsTemplateGenerator import app

if __name__ == '__main__':
    HOST = environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    FLASK_ENV_VALUE = environ.get('FLASK_DEBUG', False)
    print("Flask environment value: ", FLASK_ENV_VALUE)
    IS_DEBUG_MODE = FLASK_ENV_VALUE == 'True'
    print("IS_DEBUG_MODE: ", IS_DEBUG_MODE)
    app.run(HOST, PORT, debug=IS_DEBUG_MODE, use_reloader=False)
