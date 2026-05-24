import os
import httpx

BASE_URL = os.environ.get("TAKT_API_URL", "http://localhost:8080").rstrip("/")


def _get(path: str, **params) -> list | dict:
    with httpx.Client() as client:
        r = client.get(f"{BASE_URL}{path}", params=params)
        r.raise_for_status()
        return r.json()


def _post(path: str, body: dict) -> dict:
    with httpx.Client() as client:
        r = client.post(f"{BASE_URL}{path}", json=body)
        r.raise_for_status()
        return r.json()


def _patch(path: str, body: dict) -> dict:
    with httpx.Client() as client:
        r = client.patch(f"{BASE_URL}{path}", json=body)
        r.raise_for_status()
        return r.json()


def get_todos(context: str | None = None) -> list:
    params = {"context": context} if context else {}
    return _get("/api/v1/todos", **params)


def mark_done(item_id: int, note: str | None = None) -> dict:
    return _post(f"/api/v1/todos/{item_id}/done", {"note": note})


def get_history(item_id: int) -> list:
    return _get(f"/api/v1/todos/{item_id}/history")


def create_item(parent_id: int | None, title: str) -> dict:
    return _post("/api/v1/items", {"parent_id": parent_id, "title": title})


def set_todo(item_id: int, is_todo: bool) -> dict:
    return _patch(f"/api/v1/items/{item_id}/todo", {"is_todo": is_todo})


def get_item(item_id: int) -> dict:
    return _get(f"/api/v1/items/{item_id}")


def get_children(item_id: int) -> list:
    return _get(f"/api/v1/items/{item_id}/children")


def get_roots() -> list:
    return _get("/api/v1/items")


def get_contexts() -> list:
    return _get("/api/v1/contexts")


def health() -> dict:
    return _get("/api/v1/health")
