"""Deterministic pricing from MDM price_spec."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _apply_override(
    sku: str,
    computed: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    override = overrides.get(sku)
    if not override:
        return computed
    merged = dict(computed)
    if override.get("amount") is not None:
        merged["amount"] = float(override["amount"])
    if override.get("reason"):
        merged["override_reason"] = override["reason"]
    return merged


def compute_sku_pricing(
    service: dict[str, Any],
    pricing_facts: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    sku = service["sku"]
    ptype = service.get("pricing_type") or "FIXED"
    spec = service.get("price_spec") or {}
    currency = service.get("price_currency") or "USD"
    explanation = ""

    if ptype == "TIERED":
        dimension = spec.get("dimension") or "share_count"
        fact_value = pricing_facts.get(dimension)
        tier_label = spec.get("tier_label")
        amount = spec.get("amount")
        if fact_value is None:
            return (
                {
                    "sku": sku,
                    "status": "missing_facts",
                    "missing": [dimension],
                    "currency": currency,
                },
                f"Missing pricing fact: {dimension}",
            )
        share_count = int(fact_value)
        tier = tier_label or "default"
        if tier == "gt_50000" and share_count <= 50000:
            return (
                {"sku": sku, "status": "not_applicable", "currency": currency},
                "Tier gt_50000 not applicable",
            )
        if tier == "le_50000" and share_count > 50000:
            return (
                {"sku": sku, "status": "not_applicable", "currency": currency},
                "Tier le_50000 not applicable",
            )
        if amount is None:
            amount = service.get("price_amount")
        explanation = f"tier {tier} for {dimension}={share_count}"
        return (
            {
                "sku": sku,
                "status": "computed",
                "amount": float(amount) if amount is not None else None,
                "currency": currency,
                "pricing_type": ptype,
                "dimension": dimension,
                "tier_label": tier,
            },
            explanation,
        )

    if ptype == "RANGE":
        pmin = service.get("price_min")
        pmax = service.get("price_max")
        if pmin is not None and pmax is not None:
            mid = (float(pmin) + float(pmax)) / 2
            explanation = f"range {pmin}-{pmax}, midpoint used"
            return (
                {
                    "sku": sku,
                    "status": "computed",
                    "amount": mid,
                    "amount_min": float(pmin),
                    "amount_max": float(pmax),
                    "currency": currency,
                    "pricing_type": ptype,
                },
                explanation,
            )

    if ptype == "BASE_PLUS":
        base = _decimal(service.get("price_amount"))
        addons = spec.get("addons") or []
        addon_total = sum(float(a.get("amount") or 0) for a in addons)
        amount = float(base or 0) + addon_total
        explanation = f"base {base} + addons {addon_total}"
        return (
            {
                "sku": sku,
                "status": "computed",
                "amount": amount,
                "currency": currency,
                "pricing_type": ptype,
                "addons": addons,
            },
            explanation,
        )

    if ptype == "BASE_PLUS_VARIABLE":
        base = service.get("price_amount")
        explanation = spec.get("variable_label") or "variable component not included"
        return (
            {
                "sku": sku,
                "status": "computed",
                "amount": float(base) if base is not None else None,
                "currency": currency,
                "pricing_type": ptype,
                "variable_label": spec.get("variable_label"),
            },
            explanation,
        )

    amount = service.get("price_amount")
    if amount is None and spec.get("amount") is not None:
        amount = spec.get("amount")
    if amount is None and spec.get("note"):
        return (
            {
                "sku": sku,
                "status": "manual",
                "note": spec.get("note"),
                "fee_raw": service.get("fee_raw"),
                "currency": currency,
                "pricing_type": ptype,
            },
            spec.get("note") or "manual pricing",
        )
    return (
        {
            "sku": sku,
            "status": "computed",
            "amount": float(amount) if amount is not None else None,
            "currency": currency,
            "pricing_type": ptype,
        },
        "fixed price",
    )


def compute_pricing(
    services: list[dict[str, Any]],
    pricing_facts: dict[str, Any],
    overrides: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str], list[dict[str, Any]]]:
    computed: dict[str, Any] = {}
    explanations: dict[str, str] = {}
    recurring: list[dict[str, Any]] = []
    overrides = overrides or {}

    for service in services:
        sku = service["sku"]
        result, explanation = compute_sku_pricing(service, pricing_facts)
        if result.get("status") == "computed" and result.get("amount") is not None:
            result = _apply_override(sku, result, overrides)
        computed[sku] = result
        explanations[sku] = explanation
        if service.get("recurring") == "RECURRING" and result.get("amount") is not None:
            recurring.append(
                {
                    "sku": sku,
                    "amount": result["amount"],
                    "currency": result.get("currency"),
                    "billing_frequency": service.get("billing_frequency"),
                    "label": service.get("service_name_on_proposal"),
                }
            )

    return computed, explanations, recurring
