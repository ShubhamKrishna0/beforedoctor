import orjson


def dumps(payload: dict) -> str:
    return orjson.dumps(payload).decode("utf-8")
