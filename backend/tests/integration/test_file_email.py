import json
from pathlib import Path

from app import create_app
from app.extensions import db
from app.notifications.email import EmailMessage, deliver_now


def test_file_backend_writes_one_complete_json_file_per_email(
    migrated_database: None, tmp_path: Path
) -> None:
    app = create_app("test", overrides={"EMAIL_BACKEND": "file", "EMAIL_FILE_DIR": str(tmp_path)})
    try:
        with app.app_context():
            deliver_now(EmailMessage(to="a@example.com", subject="Hello", body="Link: x"))
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1
        assert json.loads(files[0].read_text()) == {
            "to": "a@example.com",
            "subject": "Hello",
            "body": "Link: x",
        }
        assert not list(tmp_path.glob("*.tmp"))
    finally:
        with app.app_context():
            db.engine.dispose()
