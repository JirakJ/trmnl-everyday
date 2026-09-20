"""Local CSV sales ledger. Money stays decimal and currencies never mix."""
import csv
import io
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from .common import local_path, number, screen, text

FIELDS = ("id", "date", "product", "type", "licenses", "amount", "currency")


def transactions(raw, config, now):
    columns = {field: config.get("columns", {}).get(field, field) for field in FIELDS}
    delimiter = config.get("delimiter", ",")
    if not isinstance(delimiter, str) or len(delimiter) != 1:
        raise ValueError("CSV delimiter must be one character")
    reader = csv.DictReader(io.StringIO(raw.lstrip("\ufeff")), delimiter=delimiter)
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not set(columns.values()) <= set(reader.fieldnames):
        raise ValueError("Missing or duplicate CSV columns; configure the column mapping")
    types = {str(key).upper(): value for key, value in config.get("types", {"NEW": "new", "RENEW": "renew", "REFUND": "refund"}).items()}
    seen = {}
    for index, row in enumerate(reader):
        if index >= 50_000 or None in row:
            raise ValueError("Too many rows or malformed CSV")
        values = {field: str(row.get(column) or "").strip() for field, column in columns.items()}
        if not all(values.values()) or len(values["id"]) > 256:
            raise ValueError("Every transaction needs an ID and all required fields")
        if values["id"] in seen:
            if seen[values["id"]] != values:
                raise ValueError("Conflicting duplicate transaction ID")
            continue
        seen[values["id"]] = values
        kind = types.get(values["type"].upper())
        if kind not in ("new", "renew", "refund") or not re.fullmatch(r"[A-Z]{3}", values["currency"]):
            raise ValueError("Unknown transaction type or invalid currency")
        quantity = int(values["licenses"])
        if not 1 <= quantity <= 100_000:
            raise ValueError("License quantity must be a positive integer")
        try:
            amount = Decimal(values["amount"])
        except InvalidOperation:
            raise ValueError("Use a plain decimal amount without currency symbols") from None
        if not amount.is_finite() or abs(amount) > Decimal("1000000000") or (kind != "refund" and amount < 0):
            raise ValueError("Invalid transaction amount")
        when = (datetime.strptime(values["date"], config["date_format"]) if config.get("date_format")
                else datetime.fromisoformat(values["date"].replace("Z", "+00:00")))
        if when.tzinfo is None:
            when = when.replace(tzinfo=now.tzinfo)
        when = when.astimezone(now.tzinfo)
        yield {"when": when, "product": values["product"], "kind": kind, "licenses": quantity,
               "amount": -abs(amount) if kind == "refund" else amount, "currency": values["currency"]}


def render(records, config, now, *, source, demo=False):
    currency = config["currency"]
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError("Select one three-letter currency")
    digits = int(number(config.get("money_decimals", 2), "money_decimals", 0, 4))
    selected = [row for row in records if row["when"].year == now.year and row["when"].month == now.month
                and row["when"].timestamp() <= now.timestamp()
                and (not config.get("products") or row["product"] in config["products"])]
    excluded = sum(row["currency"] != currency for row in selected)
    selected = [row for row in selected if row["currency"] == currency]
    totals = defaultdict(lambda: {"new": 0, "renew": 0, "refund": 0, "amount": Decimal(0)})
    for row in selected:
        totals[row["product"]][row["kind"]] += row["licenses"]
        totals[row["product"]]["amount"] += row["amount"]
    balance = sum((row["amount"] for row in selected), Decimal(0))
    refunds = -sum((row["amount"] for row in selected if row["kind"] == "refund"), Decimal(0))
    money = lambda value: f"{value:,.{digits}f}"
    rows = [{"time": money(data["amount"]), "title": text(product, 40),
             "detail": f'{data["new"]} new · {data["renew"]} renewed · {data["refund"]} refunded licenses'}
            for product, data in sorted(totals.items(), key=lambda item: item[1]["amount"], reverse=True)[:3]]
    return screen("Digital Product Sales", money(balance), f"{now:%B %Y} · {currency}",
                  f"Sales minus refunds · {len(selected)} transactions · top {min(3, len(totals))}/{len(totals)} products", rows, now,
                  metrics=[{"value": str(sum(row["licenses"] for row in selected if row["kind"] == "new")), "label": "New licenses"},
                           {"value": str(sum(row["licenses"] for row in selected if row["kind"] == "renew")), "label": "Renewed licenses"},
                           {"value": money(refunds), "label": f"Refunds · {currency}"}],
                  source=f"{source} · {excluded} other-currency transactions excluded", demo=demo)


def collect(config, now):
    path = local_path(config, config["csv_file"])
    if path.stat().st_size > 5_000_000:
        raise ValueError("CSV exceeds 5 MB")
    modified = datetime.fromtimestamp(path.stat().st_mtime, now.tzinfo)
    records = transactions(path.read_text(encoding="utf-8-sig"), config, now)
    return render(records, config, now, source=f"CSV file updated {modified:%d %b %H:%M}")


def demo(now):
    rows = []
    for product, kind, licenses, amount in (("Code Compass", "new", 18, "342.00"),
                                          ("Code Compass", "renew", 7, "105.00"),
                                          ("Code Compass", "refund", 1, "-19.00"),
                                          ("Schema Notes", "new", 9, "81.00"),
                                          ("Schema Notes", "renew", 5, "35.00")):
        rows.append({"when": now, "product": product, "kind": kind, "licenses": licenses,
                     "amount": Decimal(amount), "currency": "EUR"})
    return render(rows, {"currency": "EUR"}, now, source="Synthetic sales ledger", demo=True)
