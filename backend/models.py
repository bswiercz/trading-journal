"""
Trade CRUD against sqlite3, plus conversion between the JSON shape the
frontend speaks (camelCase, screenshots as base64 data URLs) and the DB row
shape (snake_case, screenshots as raw BLOB bytes + a stored mime type).

Every query is parameterized — no string-built SQL.
"""

import base64
import binascii
import json
import re
import sqlite3

from backend.db import get_db

DATA_URL_RE = re.compile(r"^data:(?P<mime>[\w./+-]+);base64,(?P<b64>.+)$", re.DOTALL)

TRADE_FIELDS = ["date", "time", "asset", "setup", "confluences",
                 "entry", "stop", "exit", "risk", "session", "thesis", "filled"]

_INSERT_SQL = """INSERT INTO trades
   (date, time, asset, setup, confluences, entry, stop, exit, risk,
    session, thesis, filled, shot_before, shot_before_mime, shot_after, shot_after_mime,
    updated_at)
   VALUES (:date, :time, :asset, :setup, :confluences, :entry, :stop, :exit, :risk,
           :session, :thesis, :filled, :shot_before, :shot_before_mime, :shot_after, :shot_after_mime,
           strftime('%Y-%m-%dT%H:%M:%fZ','now'))"""


class ValidationError(ValueError):
    pass


def _decode_shot(data_url):
    """'data:image/jpeg;base64,...' -> (bytes, mime). None/''/'' passthrough -> (None, None)."""
    if not data_url:
        return None, None
    m = DATA_URL_RE.match(data_url)
    if not m:
        raise ValidationError("Screenshot must be a base64 data URL")
    try:
        raw = base64.b64decode(m.group("b64"), validate=True)
    except (binascii.Error, ValueError) as e:
        raise ValidationError("Screenshot data is not valid base64") from e
    return raw, m.group("mime")


def _encode_shot(blob, mime):
    if not blob:
        return None
    return f"data:{mime or 'image/jpeg'};base64,{base64.b64encode(blob).decode('ascii')}"


def row_to_dict(row: sqlite3.Row, include_images: bool = True) -> dict:
    d = {
        "id": row["id"],
        "date": row["date"],
        "time": row["time"] or "",
        "asset": row["asset"] or "",
        "setup": row["setup"] or "",
        "confluences": json.loads(row["confluences"] or "[]"),
        "entry": row["entry"],
        "stop": row["stop"],
        "exit": row["exit"],
        "risk": row["risk"],
        "session": row["session"] or "",
        "thesis": row["thesis"] or "",
        "filled": bool(row["filled"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
        "hasShotBefore": bool(row["shot_before"]),
        "hasShotAfter": bool(row["shot_after"]),
    }
    if include_images:
        d["shotBefore"] = _encode_shot(row["shot_before"], row["shot_before_mime"])
        d["shotAfter"] = _encode_shot(row["shot_after"], row["shot_after_mime"])
    return d


def _validate_payload(data: dict, partial: bool = False):
    errors = []
    if not partial or "date" in data:
        if not data.get("date"):
            errors.append("date is required")
    for f in ("entry", "stop", "exit"):
        if not partial or f in data:
            v = data.get(f)
            if not isinstance(v, (int, float)):
                errors.append(f"{f} must be a number")
    if "filled" in data and not isinstance(data["filled"], bool):
        errors.append("filled must be true or false")
    if errors:
        raise ValidationError("; ".join(errors))


def _payload_to_row_kwargs(data: dict) -> dict:
    shot_before, shot_before_mime = _decode_shot(data.get("shotBefore"))
    shot_after, shot_after_mime = _decode_shot(data.get("shotAfter"))
    return {
        "date": data.get("date", ""),
        "time": data.get("time") or None,
        "asset": (data.get("asset") or "").strip(),
        "setup": data.get("setup") or "",
        "confluences": json.dumps(list(data.get("confluences") or [])),
        "entry": float(data["entry"]),
        "stop": float(data["stop"]),
        "exit": float(data["exit"]),
        "risk": float(data.get("risk") or 0),
        "session": (data.get("session") or "").strip(),
        "thesis": (data.get("thesis") or "").strip(),
        # Omitted means filled, so older clients and imports keep working.
        "filled": 1 if data.get("filled", True) else 0,
        "shot_before": shot_before,
        "shot_before_mime": shot_before_mime,
        "shot_after": shot_after,
        "shot_after_mime": shot_after_mime,
    }


def list_trades(filled: bool | None = None) -> list[dict]:
    """All trades, oldest first. Pass `filled` to return only filled / unfilled trades."""
    db = get_db()
    sql = "SELECT * FROM trades"
    params: tuple = ()
    if filled is not None:
        sql += " WHERE filled = ?"
        params = (1 if filled else 0,)
    rows = db.execute(sql + " ORDER BY date ASC, time ASC, id ASC", params).fetchall()
    return [row_to_dict(r) for r in rows]


def get_trade(trade_id: int) -> dict | None:
    db = get_db()
    row = db.execute("SELECT * FROM trades WHERE id = ?", (trade_id,)).fetchone()
    return row_to_dict(row) if row else None


def create_trade(data: dict) -> dict:
    _validate_payload(data)
    kw = _payload_to_row_kwargs(data)
    db = get_db()
    cur = db.execute(_INSERT_SQL, kw)
    db.commit()
    return get_trade(cur.lastrowid)


def bulk_create_trades(items: list[dict]) -> list[dict]:
    db = get_db()
    created_ids = []
    try:
        for data in items:
            _validate_payload(data)
            kw = _payload_to_row_kwargs(data)
            cur = db.execute(_INSERT_SQL, kw)
            created_ids.append(cur.lastrowid)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return [get_trade(i) for i in created_ids]


def update_trade(trade_id: int, data: dict) -> dict | None:
    db = get_db()
    existing = db.execute("SELECT id, filled FROM trades WHERE id = ?", (trade_id,)).fetchone()
    if not existing:
        return None
    _validate_payload(data)
    kw = _payload_to_row_kwargs(data)
    if "filled" not in data:
        kw["filled"] = existing["filled"]   # an update that omits the flag must not reset it
    kw["id"] = trade_id
    db.execute(
        """UPDATE trades SET
             date=:date, time=:time, asset=:asset, setup=:setup, confluences=:confluences,
             entry=:entry, stop=:stop, exit=:exit, risk=:risk, session=:session, thesis=:thesis,
             filled=:filled,
             shot_before=:shot_before, shot_before_mime=:shot_before_mime,
             shot_after=:shot_after, shot_after_mime=:shot_after_mime,
             updated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')
           WHERE id=:id""",
        kw,
    )
    db.commit()
    return get_trade(trade_id)


def delete_trade(trade_id: int) -> bool:
    db = get_db()
    cur = db.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
    db.commit()
    return cur.rowcount > 0


def delete_all_trades() -> int:
    db = get_db()
    cur = db.execute("DELETE FROM trades")
    db.commit()
    return cur.rowcount
