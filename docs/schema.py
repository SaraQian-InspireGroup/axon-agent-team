from __future__ import annotations

from copy import deepcopy
from typing import Any

from jsonschema import Draft202012Validator


CANONICAL_SME_PROPOSAL_TYPE = "incorp_sg_sme"
SME_PROPOSAL_TYPE_ALIASES = {"SME", "sg_sme", CANONICAL_SME_PROPOSAL_TYPE}


def normalize_proposal_type(proposal_type: str | None) -> str:
    text = str(proposal_type or "").strip()
    if text in SME_PROPOSAL_TYPE_ALIASES:
        return CANONICAL_SME_PROPOSAL_TYPE
    raise ValueError(f"Unsupported proposal_type: {proposal_type}")


SG_SME_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Smart Proposal SG SME State",
    "type": "object",
    "additionalProperties": False,
    "required": [
        "proposal_type",
        "client_profile",
        "executive_summary",
        "scope_of_services",
        "business_case_services",
    ],
    "properties": {
        "proposal_type": {"enum": sorted(SME_PROPOSAL_TYPE_ALIASES)},
        "client_profile": {"$ref": "#/$defs/client_profile"},
        "executive_summary": {"$ref": "#/$defs/text_section"},
        "scope_of_services": {"$ref": "#/$defs/titled_text_section"},
        "business_case_services": {"$ref": "#/$defs/business_case_services"},
        "appendix": {"type": "array", "items": {"$ref": "#/$defs/appendix_table"}},
        "first_total_invoice": {"type": "array", "items": {"$ref": "#/$defs/first_total_invoice_line"}},
        "deal_name": {"type": "string"},
        "file_urls": {"type": "array", "items": {"type": "string"}},
        "generated_artifacts": {"type": "array", "items": True},
        "artifact_meta": {"type": "object"},
        "introduction": {"type": "object"},
        "stage_history": {"type": "array", "items": True},
        "delivery_email": {"type": "array", "items": {"type": "string"}},
        "missing_optional": {"type": "array", "items": {"type": "string"}},
        "missing_required": {"type": "array", "items": {"type": "string"}},
        "proposal_meta": {"type": "object"},
        "business_case_status": {"type": ["string", "null"]},
        "business_cases": {"type": "array", "items": {"type": "string"}},
        "business_case_display_names": {"type": "object"},
        "current_business_case": {"type": ["string", "null"]},
        "preview_business_case": {"type": ["string", "null"]},
        "delivery_mode": {"type": ["string", "null"]},
        "delivery_email_error": {"type": ["string", "null"]},
        "pending_summary_notes": {"type": "array", "items": True},
        "first_total_invoice_skipped": {"type": "boolean"},
        "signature_partner": {"type": ["object", "null"]},
        "credentials": {"type": ["object", "null"]},
        "curriculum_vitae": {"type": ["object", "null"]},
        "timeline": {"type": ["object", "null"]},
        "value_added_services": {"type": ["object", "null"]},
        "necessary_documents": {"type": ["object", "null"]},
        "fee_description": {"type": "object"},
        "proposal_title": {"type": "object"},
        "payment_option": {"type": ["object", "array", "null"]},
        "service_slas": {"type": "object"},
        "required_overrides": {"type": "object"},
        "deal_line_items": {"type": "array", "items": True},
        "deal_currency_code": {"type": ["string", "null"]},
        "candidate_business_cases": {"type": "array", "items": True},
        "candidate_business_case_matches": {"type": "array", "items": True},
        "business_case_resolution_pass": {"type": "boolean"},
        "business_case_selections": {"type": "object"},
        "selected_services": {"type": "array", "items": True},
        "pricing_defaults": {"type": "object"},
        "pricing_overrides": {"type": "object"},
        "service_search": {"type": "object"},
        "public_listed_company": {"type": "object"},
        "listco_adhoc_services": {"type": "object"},
        "active_entities": {"type": "object"},
        "less_active_entities": {"type": "object"},
        "subsidiaries_category": {"type": ["string", "null"]},
        "listco_entity_selections": {"type": "object"},
        "stage": {"type": ["string", "null"]},
        "next_hint": {"type": ["string", "null"]},
        "plan_queue": {"type": "array", "items": True},
        "validation_errors": {"type": "array", "items": True},
        "validation_warnings": {"type": "array", "items": True},
        "last_review_services": {"type": "array", "items": True},
        "last_review_pricing": {"type": "object"},
        "translation_evidence": {"type": "object"},
    },
    "$defs": {
        "nullable_string": {"type": ["string", "null"]},
        "text_or_number": {"type": ["string", "number", "integer", "null"]},
        "timestamp": {"type": ["string", "null"]},
        "client_profile": {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "company_name",
                "contact_name",
                "contact_email",
                "contact_title",
                "company_address",
                "company_location",
                "company_abbreviation",
            ],
            "properties": {
                "company_name": {"$ref": "#/$defs/nullable_string"},
                "contact_name": {"$ref": "#/$defs/nullable_string"},
                "contact_email": {"$ref": "#/$defs/nullable_string"},
                "contact_title": {"$ref": "#/$defs/nullable_string"},
                "company_address": {"$ref": "#/$defs/nullable_string"},
                "company_location": {"$ref": "#/$defs/nullable_string"},
                "company_abbreviation": {"$ref": "#/$defs/nullable_string"},
            },
            "x-editable": True,
        },
        "text_section": {
            "type": "object",
            "additionalProperties": False,
            "required": ["paragraphs"],
            "properties": {
                "paragraphs": {"type": "array", "items": {"type": "string"}},
                "status": {"$ref": "#/$defs/nullable_string"},
                "updated_at": {"$ref": "#/$defs/timestamp"},
            },
            "x-editable": True,
            "x-localizable": True,
        },
        "titled_text_section": {
            "type": "object",
            "additionalProperties": False,
            "required": ["title", "paragraphs"],
            "properties": {
                "title": {"type": "string"},
                "paragraphs": {"type": "array", "items": {"type": "string"}},
                "status": {"$ref": "#/$defs/nullable_string"},
                "updated_at": {"$ref": "#/$defs/timestamp"},
            },
            "x-editable": True,
            "x-localizable": True,
        },
        "business_case_services": {
            "type": "object",
            "additionalProperties": False,
            "required": ["currency", "business_cases"],
            "properties": {
                "currency": {"type": "string"},
                "business_cases": {"type": "array", "items": {"$ref": "#/$defs/business_case_table"}},
                "status": {"$ref": "#/$defs/nullable_string"},
                "updated_at": {"$ref": "#/$defs/timestamp"},
                "_source_hash": {"type": "string"},
            },
            "x-editable": True,
        },
        "business_case_table": {
            "type": "object",
            "additionalProperties": True,
            "required": ["name", "currency", "services", "solution_package_instance_id"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "currency": {"type": "string"},
                "is_adhoc": {"type": "boolean"},
                "services": {"type": "array", "items": {"$ref": "#/$defs/business_case_service"}},
                "solution_package_instance_id": {"type": "string", "minLength": 1},
                "match_key": {"$ref": "#/$defs/nullable_string"},
                "canonical_name": {"$ref": "#/$defs/nullable_string"},
                "business_case_id": {"$ref": "#/$defs/nullable_string"},
            },
        },
        "business_case_service": {
            "type": "object",
            "additionalProperties": True,
            "required": ["service_instance_id", "sku", "service_name", "scope_of_work"],
            "properties": {
                "service_instance_id": {"type": "string", "minLength": 1},
                "sku": {"type": "string", "minLength": 1},
                "service_name": {"type": "string", "minLength": 1},
                "scope_of_work": {
                    "type": "array",
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "object"},
                        ]
                    },
                },
                "service_id": {"$ref": "#/$defs/nullable_string"},
                "amount": {"$ref": "#/$defs/text_or_number"},
                "currency": {"$ref": "#/$defs/nullable_string"},
                "one_off_fee": {"$ref": "#/$defs/text_or_number"},
                "recurring_fee": {"$ref": "#/$defs/text_or_number"},
                "annual_fee": {"$ref": "#/$defs/text_or_number"},
                "monthly_fee": {"$ref": "#/$defs/text_or_number"},
                "quarterly_fee": {"$ref": "#/$defs/text_or_number"},
                "total_annualized": {"$ref": "#/$defs/text_or_number"},
                "billingfrequency": {"$ref": "#/$defs/nullable_string"},
            },
        },
        "first_total_invoice_line": {
            "type": "object",
            "additionalProperties": False,
            "required": ["service_name", "currency", "price", "gst", "total", "invoice_tax_rate"],
            "properties": {
                "service_name": {"type": "string", "minLength": 1},
                "currency": {"type": "string"},
                "price": {"$ref": "#/$defs/text_or_number"},
                "gst": {"$ref": "#/$defs/text_or_number"},
                "total": {"$ref": "#/$defs/text_or_number"},
                "invoice_tax_rate": {"$ref": "#/$defs/text_or_number"},
            },
        },
        "appendix_table": {
            "type": "object",
            "additionalProperties": False,
            "required": ["table_id", "title", "columns", "rows"],
            "properties": {
                "table_id": {"type": "string", "minLength": 1},
                "title": {"type": "string"},
                "columns": {"type": "array", "items": {"$ref": "#/$defs/appendix_column"}},
                "rows": {"type": "array", "items": {"$ref": "#/$defs/appendix_row"}},
                "footnotes": {"type": "array", "items": {"type": "string"}},
                "description": {"type": "array", "items": {"type": "string"}},
                "created_at": {"$ref": "#/$defs/timestamp"},
            },
            "x-editable": True,
        },
        "appendix_column": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "label"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "label": {"type": "string"},
            },
        },
        "appendix_row": {
            "type": "object",
            "additionalProperties": False,
            "required": ["id", "cells"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "cells": {
                    "type": "object",
                    "additionalProperties": {"$ref": "#/$defs/text_or_number"},
                },
            },
        },
    },
}


def default_state(proposal_type: str = CANONICAL_SME_PROPOSAL_TYPE) -> dict[str, Any]:
    canonical_proposal_type = normalize_proposal_type(proposal_type)
    return {
        "proposal_type": canonical_proposal_type,
        "deal_name": "",
        "file_urls": [],
        "generated_artifacts": [],
        "artifact_meta": {},
        "introduction": {},
        "stage_history": [],
        "client_profile": {
            "company_name": None,
            "contact_name": None,
            "contact_email": None,
            "contact_title": None,
            "company_address": None,
            "company_location": "Singapore",
            "company_abbreviation": None,
        },
        "delivery_email": [],
        "missing_optional": [],
        "executive_summary": {"status": "template", "paragraphs": [], "updated_at": None},
        "scope_of_services": {
            "title": "Scope of Services",
            "status": "template",
            "paragraphs": [],
            "updated_at": None,
        },
        "business_case_services": {
            "currency": "SGD",
            "business_cases": [],
            "status": "template",
            "updated_at": None,
        },
    }


def validate_state_semantics(state: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    bcs = state.get("business_case_services")
    if not isinstance(bcs, dict):
        return errors
    business_cases = bcs.get("business_cases")
    if not isinstance(business_cases, list):
        return errors

    case_instance_paths: dict[str, str] = {}
    service_instance_paths: dict[str, str] = {}
    for case_index, case in enumerate(business_cases):
        if not isinstance(case, dict):
            continue
        case_instance_id = str(case.get("solution_package_instance_id") or "").strip()
        case_instance_path = f"/business_case_services/business_cases/{case_index}/solution_package_instance_id"
        if case_instance_id:
            if case_instance_id in case_instance_paths:
                errors.append(
                    {
                        "path": case_instance_path,
                        "message": (
                            "Duplicate solution_package_instance_id; each service table must have a unique instance id"
                        ),
                    }
                )
            else:
                case_instance_paths[case_instance_id] = case_instance_path

        services = case.get("services")
        if not isinstance(services, list):
            continue
        for service_index, service in enumerate(services):
            if not isinstance(service, dict):
                continue
            service_instance_id = str(service.get("service_instance_id") or "").strip()
            service_instance_path = (
                f"/business_case_services/business_cases/{case_index}/services/{service_index}/service_instance_id"
            )
            if service_instance_id:
                if service_instance_id in service_instance_paths:
                    errors.append(
                        {
                            "path": service_instance_path,
                            "message": (
                                "Duplicate service_instance_id; use the service row instance id rather than service_id"
                            ),
                        }
                    )
                else:
                    service_instance_paths[service_instance_id] = service_instance_path

    return errors


class StateSchemaRegistry:
    def __init__(self) -> None:
        schema = deepcopy(SG_SME_SCHEMA)
        self._schemas = {
            CANONICAL_SME_PROPOSAL_TYPE: schema,
            "SME": deepcopy(schema),
            "sg_sme": deepcopy(schema),
        }

    def schema_for(self, proposal_type: str) -> dict[str, Any]:
        normalized = proposal_type if proposal_type in self._schemas else normalize_proposal_type(proposal_type)
        try:
            return deepcopy(self._schemas[normalized])
        except KeyError as exc:
            raise ValueError(f"Unknown proposal_type: {proposal_type}") from exc

    def validate(self, state: dict[str, Any]) -> list[dict[str, str]]:
        proposal_type = str(state.get("proposal_type") or CANONICAL_SME_PROPOSAL_TYPE)
        validator = Draft202012Validator(self.schema_for(proposal_type))
        schema_errors = sorted(validator.iter_errors(state), key=lambda error: list(error.path))
        errors = [
            {
                "path": "/" + "/".join(str(part) for part in error.path),
                "message": error.message,
            }
            for error in schema_errors
        ]
        return errors + validate_state_semantics(state)
