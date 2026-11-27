#!/usr/bin/env python3
"""Считает заказы и выручку по артикулам и дням.

Читает sales.csv, пишет daily_by_sku.csv.
Используется только стандартная библиотека Python.
"""

import csv
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

COLUMNS = ["order_id", "order_date", "sku", "quantity", "price", "status"]
ALLOWED_STATUSES = {"delivered", "cancelled"}
BASE_DIR = Path(__file__).resolve().parent
INPUT_PATH = BASE_DIR / "sales.csv"
OUTPUT_PATH = BASE_DIR / "daily_by_sku.csv"


def normalize_status(raw_status):
    """Приводит статус к одному виду: 'DELIVERED ' -> 'delivered'."""
    status = raw_status.strip().lower()
    if status == "canceled":
        status = "cancelled"
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Unknown status: {raw_status!r}")
    return status


def read_orders(path):
    """Читает CSV и возвращает список строк с нормализованным статусом."""
    orders = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != COLUMNS:
            raise ValueError(
                f"Expected columns {COLUMNS}, got {reader.fieldnames}"
            )
        for line_number, row in enumerate(reader, start=2):
            if None in row or any(row[column] is None for column in COLUMNS):
                raise ValueError(f"Line {line_number}: wrong number of columns")
            orders.append(
                {
                    "order_id": row["order_id"].strip(),
                    "order_date": row["order_date"].strip(),
                    "sku": row["sku"].strip(),
                    "quantity": row["quantity"].strip(),
                    "price": row["price"].strip(),
                    "status": normalize_status(row["status"]),
                }
            )
    return orders


def deduplicate(orders):
    """Убирает полные дубли строк, сохраняя порядок."""
    seen = set()
    unique = []
    for order in orders:
        key = tuple(order[column] for column in COLUMNS)
        if key not in seen:
            seen.add(key)
            unique.append(order)
    return unique


def aggregate(orders):
    """Считает orders и revenue по ключу (sku, order_date)."""
    totals = defaultdict(lambda: {"orders": 0, "revenue": Decimal("0")})
    for order in orders:
        key = (order["sku"], order["order_date"])
        totals[key]["orders"] += 1

        if order["status"] != "delivered":
            continue

        try:
            quantity = int(order["quantity"])
            price = Decimal(order["price"])
        except (ValueError, InvalidOperation):
            raise ValueError(
                f"Order {order['order_id']}: invalid quantity/price "
                f"({order['quantity']!r}, {order['price']!r})"
            )

        totals[key]["revenue"] += quantity * price
    return totals


def write_report(totals, path):
    """Пишет daily_by_sku.csv, сортируя по sku и дате."""
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["sku", "order_date", "orders", "revenue"])
        for sku, order_date in sorted(totals):
            row = totals[(sku, order_date)]
            writer.writerow(
                [sku, order_date, row["orders"], format(row["revenue"], "f")]
            )


def main():
    orders = deduplicate(read_orders(INPUT_PATH))
    totals = aggregate(orders)
    write_report(totals, OUTPUT_PATH)
    print(
        f"Done: {OUTPUT_PATH.name}, rows: {len(totals)}, "
        f"unique orders: {len(orders)}"
    )


if __name__ == "__main__":
    main()
