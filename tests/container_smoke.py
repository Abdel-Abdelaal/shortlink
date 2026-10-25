"""Exercise the actual container over HTTP, including persistence across restart."""

import argparse
import json
import time
from urllib.error import URLError
from urllib.request import Request, urlopen


def request(path: str, *, body: dict[str, str] | None = None) -> dict[str, object]:
    """Send a bounded request to the local container only."""
    data = json.dumps(body).encode() if body is not None else None
    response = urlopen(
        Request(
            "http://127.0.0.1:8000" + path,
            data=data,
            headers={"Content-Type": "application/json"},
        ),
        timeout=3,
    )
    with response:
        result: dict[str, object] = json.load(response)
        return result


def main() -> None:
    """Check readiness, create a record or verify the persisted record."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["create", "persisted"])
    mode = parser.parse_args().mode
    for attempt in range(30):
        try:
            if request("/health") != {"status": "ok"}:
                msg = "unexpected health response"
                raise RuntimeError(msg)
            break
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 29:
                raise
            time.sleep(1)
    if mode == "create":
        result = request(
            "/links",
            body={"target_url": "https://example.com/container", "code": "persisted"},
        )
    else:
        result = request("/links/persisted")
    if result.get("target_url") != "https://example.com/container":
        msg = "container record did not survive correctly"
        raise RuntimeError(msg)


if __name__ == "__main__":
    main()
