from inventory.stock import Ledger


def test_add_and_total():
    l = Ledger()
    l.add("a", 2, 150)
    l.add("a", 1, 150)
    assert l.total_value_cents() == 450
