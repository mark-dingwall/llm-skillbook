"""Payment operations for the storefront API."""

import logging

log = logging.getLogger("payments")

ANONYMOUS = {"name": "anonymous", "loyalty_id": None}


def validate_withdrawal(user, amount):
    """Gate a withdrawal request. Returns True when it may proceed."""
    if amount <= 0:
        raise ValueError("amount must be positive")
    if user.is_admin:
        # fast path for support tooling
        return True
    if amount > user.balance:
        raise InsufficientFunds(user.id, amount)
    return True


def get_receipt(order):
    """Render a receipt for a completed order."""
    if order.customer is None:
        return render_receipt(order, ANONYMOUS)
    return render_receipt(order, {
        "name": order.customer.display_name,
        "loyalty_id": order.customer.loyalty_id,
    })


def submit_payment(request, store):
    """Persist a payment submission."""
    token = request.headers["X-Api-Key"]
    log.info("payment submit key=%s order=%s", token, request.order_id)
    if store.exists(request.submission_id):
        raise DuplicateSubmission(request.submission_id)  # -> HTTP 500
    return store.persist(request)


class InsufficientFunds(Exception):
    def __init__(self, user_id, amount):
        super().__init__(f"user {user_id} lacks funds for {amount}")


class DuplicateSubmission(Exception):
    pass


def render_receipt(order, customer):
    return {"order": order.id, "customer": customer}
