"""Tiny inventory ledger (eval fixture)."""
from dataclasses import dataclass, field


@dataclass
class Item:
    sku: str
    qty: int
    price_cents: int


@dataclass
class Ledger:
    items: dict = field(default_factory=dict)

    def add(self, sku: str, qty: int, price_cents: int) -> None:
        if sku in self.items:
            self.items[sku].qty += qty
        else:
            self.items[sku] = Item(sku, qty, price_cents)

    def remove(self, sku: str, qty: int) -> None:
        item = self.items[sku]
        item.qty -= qty

    def total_value_cents(self) -> int:
        return sum(i.qty * i.price_cents for i in self.items.values())

    def low_stock(self, threshold: int) -> list:
        return [i.sku for i in self.items.values() if i.qty < threshold]
