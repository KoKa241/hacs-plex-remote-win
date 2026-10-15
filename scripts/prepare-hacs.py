"""Set repository metadata before publishing: python scripts/prepare-hacs.py owner/repo."""

import argparse
import json
import re
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("repository", help="GitHub owner/repository")
args = parser.parse_args()
if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+", args.repository):
    parser.error("Expected GitHub owner/repository")
path = Path(__file__).resolve().parents[1] / "custom_components/plex_pc_remote/manifest.json"
data = json.loads(path.read_text())
data.update(
    documentation=f"https://github.com/{args.repository}",
    issue_tracker=f"https://github.com/{args.repository}/issues",
    codeowners=["@" + args.repository.split("/")[0]],
)
path.write_text(json.dumps(data, indent=2) + "\n")
print(f"Updated {path}. Publish this repository to GitHub, then add it to HACS as Integration.")
