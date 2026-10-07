#!/usr/bin/env python3
"""Read the emails PropFlow "sent" locally (EMAIL_BACKEND=file), newest first, with their links.

Usage: python3 scripts/mailbox.py [-n COUNT] [--to ADDRESS]
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

MAIL_DIR = Path("/tmp/propflow-mail")

parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("-n", type=int, default=5, help="how many emails to show (default 5)")
parser.add_argument("--to", help="only emails to this address")
args = parser.parse_args()

shown = 0
for path in sorted(MAIL_DIR.glob("*.json"), reverse=True):
    message = json.loads(path.read_text())
    if args.to and message["to"].lower() != args.to.lower():
        continue
    sent = datetime.fromtimestamp(int(path.name.split("-")[0]) / 1e9)
    print(f"── {sent:%Y-%m-%d %H:%M:%S}  to {message['to']}")
    print(f"   {message['subject']}")
    for link in re.findall(r"https?://\S+", message["body"]):
        print(f"   → {link}")
    shown += 1
    if shown >= args.n:
        break
if shown == 0:
    print(f"No emails yet in {MAIL_DIR}" + (f" for {args.to}" if args.to else "") + ".")
