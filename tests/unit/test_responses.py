from fastapi.responses import JSONResponse
from starlette.background import BackgroundTask

from shortlink.api.responses import head_response


def test_head_preserves_rendered_metadata_without_mutating_get() -> None:
    background = BackgroundTask(lambda: None)
    response = JSONResponse({"message": "\u2603"}, background=background)
    response.raw_headers.extend([(b"vary", b"accept"), (b"vary", b"origin")])
    original_body = response.body
    head = head_response(response)
    assert head.body == b""
    assert head.status_code == response.status_code
    assert head.media_type == response.media_type
    assert head.raw_headers == response.raw_headers
    assert head.raw_headers is not response.raw_headers
    assert head.headers.getlist("vary") == ["accept", "origin"]
    assert int(head.headers["content-length"]) == len(original_body)
    assert response.body == original_body
    assert head.background is background
