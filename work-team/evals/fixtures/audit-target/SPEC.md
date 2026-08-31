# inventory spec

- `Ledger.remove(sku, qty)`: raise `ValueError` if `qty` exceeds current stock.
- `Ledger.low_stock(threshold)`: SKUs with `qty <= threshold`.
- CSV rows are `sku,qty,price_dollars`; the ledger stores cents.
- `total_value_cents` = sum of `qty * price_cents`.
