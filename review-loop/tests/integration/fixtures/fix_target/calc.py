"""A tiny target under review with one latent, reviewer-findable bug.

``discount`` is meant to subtract a percentage but adds it -- no gate catches
this (it imports and runs cleanly); a reviewer must find it, and the sole
authorized FIX window must repair it.
"""


def discount(price, percent):
    # BUG: should subtract the percentage, not add it.
    return price + price * percent / 100
