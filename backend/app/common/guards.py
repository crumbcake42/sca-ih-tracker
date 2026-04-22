from fastapi import HTTPException


def assert_deletable(refs: dict[str, int]) -> None:
    blocked_by = [label for label, count in refs.items() if count > 0]
    if blocked_by:
        raise HTTPException(status_code=409, detail={"blocked_by": blocked_by})
