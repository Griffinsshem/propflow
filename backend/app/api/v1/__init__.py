"""Version 1 of the public API. A future v2 registers its own blueprints alongside it."""

from flask_smorest import Api

from app.audit.routes import blp as audit_blp
from app.auth.routes import blp as auth_blp
from app.organizations.invitation_routes import blp as invitations_blp
from app.organizations.member_routes import blp as members_blp
from app.organizations.routes import blp as organizations_blp
from app.properties.routes import properties_blp, units_blp


def register_v1(api: Api) -> None:
    for blueprint in (
        auth_blp,
        organizations_blp,
        invitations_blp,
        members_blp,
        properties_blp,
        units_blp,
        audit_blp,
    ):
        api.register_blueprint(blueprint)
