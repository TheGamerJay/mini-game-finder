from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from models import db, CreditTxn, User, Transaction
import json

class InsufficientCredits(Exception): ...
class DoubleCharge(Exception): ...
class CreditError(Exception): ...
class NotEnoughCredits(CreditError): ...

def _commit(): db.session.commit()
def balance(u:User)->int: return int(u.mini_word_credits or 0)

def _debit(u:User, amount:int, reason:str, idem:str|None)->CreditTxn:
    if amount<=0: raise ValueError("amount>0 required")
    if balance(u)<amount: raise InsufficientCredits()
    u.mini_word_credits -= amount
    t = CreditTxn(user_id=u.id, amount_delta=-amount, reason=reason, idempotency_key=idem)
    db.session.add(t)
    try:
        db.session.flush(); _commit()
    except IntegrityError:
        db.session.rollback()
        raise DoubleCharge()
    return t

def _refund(u:User, amount:int, reason:str, ref_id:int|None=None)->CreditTxn:
    u.mini_word_credits += amount
    t = CreditTxn(user_id=u.id, amount_delta=+amount, reason=reason, ref_txn_id=ref_id)
    db.session.add(t); _commit(); return t

@contextmanager
def spend_credits(u:User, cost:int, reason:str, *, idem:str|None=None):
    debit = _debit(u, cost, reason, idem)
    try:
        yield debit
    except Exception:
        _refund(u, cost, f"refund:{reason}", ref_id=debit.id)
        raise

def explicit_refund_for(debit_txn:CreditTxn, reason_suffix="manual"):
    u = User.query.get(debit_txn.user_id)
    return _refund(u, -debit_txn.amount_delta, f"refund:{debit_txn.reason}:{reason_suffix}", ref_id=debit_txn.id)

# Enhanced gaming platform credit functions
def _lock_user_row(user_id: int):
    """Lock user row for atomic credit operations"""
    return db.session.execute(
        text("SELECT id, mini_word_credits FROM users WHERE id=:uid FOR UPDATE"),
        {"uid": user_id}
    ).first()

def spend_credits_v2(user_id: int, amount: int, kind: str, meta=None):
    """
    Thread-safe credit spending for gaming platform

    Args:
        user_id: User ID
        amount: Credits to spend (must be positive)
        kind: Transaction type (e.g., 'hint', 'continue', 'boost', 'war_boost', 'war_unboost')
        meta: Optional metadata dict

    Returns:
        New credit balance

    Raises:
        CreditError: User not found
        NotEnoughCredits: Insufficient credits
    """
    assert amount > 0, "Amount must be positive"

    row = _lock_user_row(user_id)
    if not row:
        raise CreditError("User not found")

    current_credits = row.mini_word_credits or 0
    if current_credits < amount:
        raise NotEnoughCredits(f"Need {amount} credits, have {current_credits}")

    new_balance = current_credits - amount

    # Update user balance
    db.session.execute(
        text("UPDATE users SET mini_word_credits=:c WHERE id=:uid"),
        {"c": new_balance, "uid": user_id}
    )

    # Log transaction in new gaming table
    db.session.add(Transaction(
        user_id=user_id,
        kind=kind,
        amount_delta=-amount,
        meta_json=json.dumps(meta or {})
    ))

    db.session.commit()
    return new_balance

def add_credits_v2(user_id: int, amount: int, kind: str, amount_usd=None, ref=None, meta=None):
    """
    Thread-safe credit addition for gaming platform

    Args:
        user_id: User ID
        amount: Credits to add (must be positive)
        kind: Transaction type (e.g., 'purchase', 'bonus', 'war_prize')
        amount_usd: USD amount for purchases
        ref: Reference code
        meta: Optional metadata dict

    Returns:
        New credit balance

    Raises:
        CreditError: User not found
    """
    assert amount > 0, "Amount must be positive"

    row = _lock_user_row(user_id)
    if not row:
        raise CreditError("User not found")

    current_credits = row.mini_word_credits or 0
    new_balance = current_credits + amount

    # Update user balance
    db.session.execute(
        text("UPDATE users SET mini_word_credits=:c WHERE id=:uid"),
        {"c": new_balance, "uid": user_id}
    )

    # Log transaction in new gaming table
    db.session.add(Transaction(
        user_id=user_id,
        kind=kind,
        amount_delta=amount,
        amount_usd=amount_usd,
        ref_code=ref,
        meta_json=json.dumps(meta or {})
    ))

    db.session.commit()
    return new_balance

def get_balance(user_id: int) -> int:
    """Get current credit balance"""
    user = User.query.get(user_id)
    return user.mini_word_credits if user else 0