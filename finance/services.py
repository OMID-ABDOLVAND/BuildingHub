"""Expense allocation algorithms with deterministic remainder distribution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationInput:
    unit_id: int
    resident_count: int
    area_sqm: int
    custom_amount: int | None = None


def distribute_equal(total: int, items: list[AllocationInput]) -> dict[int, int]:
    n = len(items)
    if n == 0:
        raise ValueError("هیچ واحدی برای تقسیم انتخاب نشده است.")
    base = total // n
    remainder = total % n
    result: dict[int, int] = {}
    # Deterministic: sort by unit_id ascending; give +1 to first `remainder` units
    ordered = sorted(items, key=lambda x: x.unit_id)
    for i, item in enumerate(ordered):
        result[item.unit_id] = base + (1 if i < remainder else 0)
    return result


def distribute_by_weight(
    total: int,
    items: list[AllocationInput],
    weight_fn,
) -> dict[int, int]:
    if not items:
        raise ValueError("هیچ واحدی برای تقسیم انتخاب نشده است.")
    weights = [(item, int(weight_fn(item))) for item in items]
    total_weight = sum(w for _, w in weights)
    if total_weight <= 0:
        raise ValueError("مجموع وزن واحدها باید بزرگ‌تر از صفر باشد.")

    raw = []
    assigned = 0
    for item, w in weights:
        share = (total * w) // total_weight
        raw.append([item.unit_id, share, (total * w) % total_weight])
        assigned += share

    remainder = total - assigned
    # Give remaining toman to units with largest leftover fractions, then unit_id
    raw.sort(key=lambda x: (-x[2], x[0]))
    for i in range(remainder):
        raw[i][1] += 1

    return {unit_id: amount for unit_id, amount, _ in raw}


def distribute_resident(total: int, items: list[AllocationInput]) -> dict[int, int]:
    return distribute_by_weight(total, items, lambda i: i.resident_count)


def distribute_area(total: int, items: list[AllocationInput]) -> dict[int, int]:
    return distribute_by_weight(total, items, lambda i: i.area_sqm)


def distribute_custom(total: int, items: list[AllocationInput]) -> dict[int, int]:
    if not items:
        raise ValueError("هیچ واحدی برای تقسیم انتخاب نشده است.")
    result: dict[int, int] = {}
    for item in items:
        if item.custom_amount is None:
            raise ValueError(f"سهم سفارشی واحد {item.unit_id} مشخص نشده است.")
        if item.custom_amount < 0:
            raise ValueError("سهم سفارشی نمی‌تواند منفی باشد.")
        result[item.unit_id] = int(item.custom_amount)
    if sum(result.values()) != total:
        raise ValueError("جمع سهم‌های سفارشی باید دقیقاً برابر مبلغ کل باشد.")
    return result


def compute_allocations(
    method: str,
    total: int,
    items: list[AllocationInput],
) -> dict[int, int]:
    if total <= 0:
        raise ValueError("مبلغ کل باید بزرگ‌تر از صفر باشد.")
    if method == "equal":
        result = distribute_equal(total, items)
    elif method == "resident":
        result = distribute_resident(total, items)
    elif method == "area":
        result = distribute_area(total, items)
    elif method == "custom":
        result = distribute_custom(total, items)
    else:
        raise ValueError("روش تقسیم نامعتبر است.")

    if sum(result.values()) != total:
        raise ValueError("خطای داخلی: جمع سهم‌ها با مبلغ کل برابر نیست.")
    return result