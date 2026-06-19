from unittest.mock import AsyncMock, patch

from app.proposal.catalog import (
    SelectionResolveResult,
    looks_like_display_name,
    resolve_services_for_selection,
)


def test_looks_like_display_name():
    assert looks_like_display_name("Special Purpose Financial Statements & Company Tax Return")
    assert not looks_like_display_name("TA01")


def test_resolve_services_by_display_name_fallback():
    services = [
        {
            "sku": "TA19",
            "service_name_on_proposal": "Special Purpose Financial Statements & Company Tax Return",
            "billing_frequency": "ANNUALLY",
            "recurring": "RECURRING",
            "pricing_type": "FIXED",
            "price_currency": "AUD",
            "price_amount": 100.0,
            "price_spec": {},
        }
    ]

    async def _fake_resolve(category_id: str, identifiers: list[str]) -> SelectionResolveResult:
        assert category_id == "au-services"
        assert identifiers == ["Special Purpose Financial Statements & Company Tax Return"]
        return SelectionResolveResult(
            services=services,
            unresolved=[],
            resolved_by_name=identifiers,
        )

    with patch("app.proposal.catalog._resolve_services_for_selection", new=AsyncMock(side_effect=_fake_resolve)):
        result = resolve_services_for_selection(
            "au-services",
            ["Special Purpose Financial Statements & Company Tax Return"],
        )

    assert len(result.services) == 1
    assert result.services[0]["sku"] == "TA19"
    assert result.resolved_by_name == ["Special Purpose Financial Statements & Company Tax Return"]
