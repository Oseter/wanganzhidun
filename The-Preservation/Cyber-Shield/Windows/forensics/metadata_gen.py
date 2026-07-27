import json
import os
from datetime import datetime


def write_metadata(event_dir: str, ts: datetime, source_app: str,
                   kind: str, text: str, attachments: dict):
    meta = {
        "timestamp": ts.isoformat(),
        "source": source_app,
        "type": kind,
        "text_preview": text[:200],
        "screenshots": attachments.get("screenshots", []),
        "replay": attachments.get("replay"),
        "raw_text": attachments.get("raw_text"),
    }
    meta_path = os.path.join(event_dir, "metadata.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
