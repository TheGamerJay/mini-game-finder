from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, Transaction
from services.credits import spend_credits_v2, NotEnoughCredits
import json

wallet_bp = Blueprint("wallet", __name__)

@wallet_bp.route("/api/hint/unlock", methods=["POST"])
@login_required
def unlock_hint():
    word = (request.json or {}).get("word","").strip()
    try:
        remaining = spend_credits_v2(current_user.id, 1, "hint", meta={"word": word})
        hint = f"Starts with '{word[:1]}' and ends with '{word[-1:]}'" if word else "Pick a word first."
        return jsonify({"success": True, "remaining": remaining, "hint": hint})
    except NotEnoughCredits as e:
        return jsonify({"success": False, "error": str(e)}), 400

@wallet_bp.route("/api/game/continue", methods=["POST"])
@login_required
def game_continue():
    try:
        remaining = spend_credits_v2(current_user.id, 1, "continue", meta={"mode":"word_search"})
        return jsonify({"success": True, "remaining": remaining})
    except NotEnoughCredits as e:
        return jsonify({"success": False, "error": str(e)}), 400

@wallet_bp.route("/api/wallet/transactions", methods=["GET"])
@login_required
def list_transactions():
    rows = (Transaction.query
            .filter_by(user_id=current_user.id)
            .order_by(Transaction.created_at.desc())
            .limit(200).all())

    transactions = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r.meta_json or '{}')
        except:
            pass

        transactions.append({
            "id": r.id,
            "created_at": r.created_at.isoformat(),
            "kind": r.kind,
            "amount_delta": r.amount_delta,
            "amount_usd": float(r.amount_usd) if r.amount_usd is not None else None,
            "ref_code": r.ref_code,
            "meta": meta
        })

    return jsonify({
        "current_balance": current_user.mini_word_credits,
        "transactions": transactions
    })