import logging
from flask import Flask
from flask_cors import CORS

from routes.deploy import deploy_bp
from routes.projects import projects_bp


def create_app() -> Flask:
    app = Flask(__name__)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    app.register_blueprint(deploy_bp)
    app.register_blueprint(projects_bp)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
