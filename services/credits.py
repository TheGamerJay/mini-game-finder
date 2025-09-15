from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError
from models import db, CreditTxn, User

class InsufficientCredits(Exception): ...
class DoubleCharge(Exception): ...

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