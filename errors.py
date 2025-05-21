from flask import render_template, request, jsonify
from werkzeug.exceptions import HTTPException
import logging

logger = logging.getLogger(__name__)

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        logger.warning(f'Page not found: {request.url}')
        if request.is_json:
            return jsonify({'error': 'Not found'}), 404
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f'Server Error: {str(error)}')
        if request.is_json:
            return jsonify({'error': 'Internal server error'}), 500
        return render_template('500.html'), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        logger.warning(f'Forbidden access: {request.url}')
        if request.is_json:
            return jsonify({'error': 'Forbidden'}), 403
        return render_template('403.html'), 403

    @app.errorhandler(401)
    def unauthorized_error(error):
        logger.warning(f'Unauthorized access: {request.url}')
        if request.is_json:
            return jsonify({'error': 'Unauthorized'}), 401
        return render_template('401.html'), 401

    @app.errorhandler(HTTPException)
    def handle_exception(e):
        logger.error(f'HTTP Exception: {str(e)}')
        if request.is_json:
            return jsonify({
                "code": e.code,
                "name": e.name,
                "description": e.description,
            }), e.code
        return render_template('error.html', error=e), e.code 