"""Version 1 of the public API. A future v2 registers its own blueprints alongside it."""

from flask_smorest import Api

from app.auth.routes import blp as auth_blp


def register_v1(api: Api) -> None:
    api.register_blueprint(auth_blp)
