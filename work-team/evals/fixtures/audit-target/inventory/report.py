from .stock import Ledger


def format_report(ledger: Ledger) -> str:
    lines = [f"{i.sku}: {i.qty} @ {i.price_cents / 100:.2f}" for i in ledger.items.values()]
    lines.append(f"TOTAL: {ledger.total_value_cents() / 100:.2f}")
    return "\n".join(lines)


def parse_csv_line(line: str):
    sku, qty, price = line.split(",")
    return sku.strip(), int(qty), int(price)
