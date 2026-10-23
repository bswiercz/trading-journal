from flask import Blueprint, jsonify, request

from backend.auth import jwt_required
from backend import models

bp = Blueprint("trades", __name__, url_prefix="/api/trades")


_BOOL_STRINGS = {"true": True, "1": True, "false": False, "0": False}


@bp.get("")
@jwt_required
def list_trades():
    """Optional `?filled=true|false` narrows the list; omitted returns every trade."""
    raw = request.args.get("filled")
    filled = None
    if raw is not None:
        filled = _BOOL_STRINGS.get(raw.strip().lower())
        if filled is None:
            return jsonify(error="filled must be true or false"), 400
    return jsonify(models.list_trades(filled=filled))


@bp.post("")
@jwt_required
def create_trade():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400
    try:
        trade = models.create_trade(data)
    except models.ValidationError as e:
        return jsonify(error=str(e)), 400
    return jsonify(trade), 201


@bp.post("/bulk")
@jwt_required
def bulk_create():
    data = request.get_json(silent=True)
    if not isinstance(data, list):
        return jsonify(error="Expected a JSON array"), 400
    if len(data) > 5000:
        return jsonify(error="Too many trades in one request"), 400
    try:
        trades = models.bulk_create_trades(data)
    except models.ValidationError as e:
        return jsonify(error=str(e)), 400
    return jsonify(trades), 201


@bp.get("/<int:trade_id>")
@jwt_required
def get_trade(trade_id):
    trade = models.get_trade(trade_id)
    if not trade:
        return jsonify(error="Trade not found"), 404
    return jsonify(trade)


@bp.put("/<int:trade_id>")
@jwt_required
def update_trade(trade_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object"), 400
    try:
        trade = models.update_trade(trade_id, data)
    except models.ValidationError as e:
        return jsonify(error=str(e)), 400
    if not trade:
        return jsonify(error="Trade not found"), 404
    return jsonify(trade)


@bp.delete("/<int:trade_id>")
@jwt_required
def delete_trade(trade_id):
    if not models.delete_trade(trade_id):
        return jsonify(error="Trade not found"), 404
    return "", 204


@bp.delete("")
@jwt_required
def delete_all():
    count = models.delete_all_trades()
    return jsonify(deleted=count)
