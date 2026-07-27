import json
import sys
from typing import Optional


def send_msg(pipe, msg: dict):
    line = json.dumps(msg, ensure_ascii=False) + "\n"
    pipe.write(line.encode("utf-8"))
    pipe.flush()


def recv_msg(pipe) -> Optional[dict]:
    line = pipe.readline()
    if not line:
        return None
    return json.loads(line)


def send_stdout(msg: dict):
    send_msg(sys.stdout, msg)


def recv_stdin() -> Optional[dict]:
    return recv_msg(sys.stdin)
