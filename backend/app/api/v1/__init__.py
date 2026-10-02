"""Version 1 of the public API. A future v2 registers its own blueprints alongside it."""

from flask_smorest import Api

from app.audit.routes import blp as audit_blp
from app.auth.routes import blp as auth_blp
from app.organizations.routes import blp as organizations_blp


def register_v1(api: Api) -> None:
    for blueprint in (auth_blp, organizations_blp, audit_blp):
        api.register_blueprint(blueprint)
