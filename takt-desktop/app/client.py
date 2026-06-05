import os
import httpx

BASE_URL = os.environ.get("TAKT_API_URL", "http://127.0.0.1:8080").rstrip("/")
TIMEOUT = 10.0

_client: httpx.Client | None = None


def reset():
    global _client
    if _client and not _client.is_closed:
        _client.close()
    _client = None


def _http() -> httpx.Client:
    global _client, BASE_URL
    if _client is None or _client.is_closed:
        _client = httpx.Client(timeout=TIMEOUT)
    return _client


def _get(path: str, **params):
    r = _http().get(f"{BASE_URL}{path}", params={k: v for k, v in params.items() if v is not None})
    r.raise_for_status()
    return r.json()


def _post(path: str, body: dict):
    r = _http().post(f"{BASE_URL}{path}", json=body)
    r.raise_for_status()
    return r.json()


def _patch(path: str, body: dict):
    r = _http().patch(f"{BASE_URL}{path}", json=body)
    r.raise_for_status()
    return r.json()


def _put(path: str, body):
    r = _http().put(f"{BASE_URL}{path}", json=body)
    r.raise_for_status()
    return r.json()


def _delete(path: str):
    r = _http().delete(f"{BASE_URL}{path}")
    r.raise_for_status()


def get_roots():
    return _get("/api/v1/items")

def get_tree(context_ids: list[int] | None = None, root_ids: list[int] | None = None,
             hide_done: bool = False):
    params = []
    for cid in (context_ids or []):
        params.append(("context_id", cid))
    for rid in (root_ids or []):
        params.append(("root_id", rid))
    params.append(("hide_done", "true" if hide_done else "false"))
    r = _http().get(f"{BASE_URL}/api/v1/items/tree", params=params)
    r.raise_for_status()
    return r.json()

def get_children(item_id: int):
    return _get(f"/api/v1/items/{item_id}/children")

def get_item(item_id: int):
    return _get(f"/api/v1/items/{item_id}")

def create_item(parent_id, title: str):
    return _post("/api/v1/items", {"parent_id": parent_id, "title": title})

def update_item(item_id: int, **fields):
    return _patch(f"/api/v1/items/{item_id}", fields)

def move_item(item_id: int, parent_id, order_index: int):
    return _patch(f"/api/v1/items/{item_id}/move", {"parent_id": parent_id, "order_index": order_index})

def delete_item(item_id: int):
    _delete(f"/api/v1/items/{item_id}")

def set_todo(item_id: int, is_todo: bool):
    return _patch(f"/api/v1/items/{item_id}/todo", {"is_todo": is_todo})

def set_recurring(item_id: int, is_recurring: bool, interval: str | None = None):
    return _patch(f"/api/v1/items/{item_id}/recurring", {"is_recurring": is_recurring, "recurring_interval": interval})

def set_done(item_id: int, is_done: bool):
    return _patch(f"/api/v1/items/{item_id}/done", {"is_done": is_done})

def set_variation(item_id: int, variation_list_id: int | None, mode: str | None, index: int = 0):
    return _patch(f"/api/v1/items/{item_id}/variation", {
        "variation_list_id": variation_list_id,
        "variation_mode": mode,
        "variation_index": index,
    })

def get_variations():
    return _get("/api/v1/variations")

def set_contexts(item_id: int, context_ids: list[int]):
    return _put(f"/api/v1/items/{item_id}/contexts", context_ids)

def get_todos(context_ids: list[int] | None = None, root_ids: list[int] | None = None,
              include_done: bool = False):
    params = []
    for cid in (context_ids or []):
        params.append(("context_id", cid))
    for rid in (root_ids or []):
        params.append(("root_id", rid))
    params.append(("include_done", "true" if include_done else "false"))
    r = _http().get(f"{BASE_URL}/api/v1/todos", params=params)
    r.raise_for_status()
    return r.json()

def mark_done(item_id: int, note: str | None = None):
    return _post(f"/api/v1/todos/{item_id}/done", {"note": note})

def get_history(item_id: int):
    return _get(f"/api/v1/todos/{item_id}/history")

def get_all_history(context_ids: list[int] | None = None, root_ids: list[int] | None = None):
    params = []
    for cid in (context_ids or []):
        params.append(("context_id", cid))
    for rid in (root_ids or []):
        params.append(("root_id", rid))
    r = _http().get(f"{BASE_URL}/api/v1/todos/history", params=params)
    r.raise_for_status()
    return r.json()

def delete_history(before: str | None = None) -> int:
    params = {"before": before} if before else None
    r = _http().delete(f"{BASE_URL}/api/v1/todos/history", params=params)
    r.raise_for_status()
    return r.json().get("deleted", 0)

def delete_history_entry(log_id: int):
    _delete(f"/api/v1/todos/history/{log_id}")

def get_contexts():
    return _get("/api/v1/contexts")

def create_context(name: str, color: str):
    return _post("/api/v1/contexts", {"name": name, "color": color})

def update_context(context_id: int, name: str, color: str):
    return _patch(f"/api/v1/contexts/{context_id}", {"name": name, "color": color})

def delete_context(context_id: int):
    _delete(f"/api/v1/contexts/{context_id}")

def health():
    return _get("/api/v1/health")
