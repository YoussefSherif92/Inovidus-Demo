import json
import re
import unicodedata

from database import get_connection


def normalize_text(value):
    text = unicodedata.normalize("NFKC", value or "")
    return " ".join(text.casefold().split())


def normalize_address(value):
    text = normalize_text(value)
    text = re.sub(r"str\.?(?=\s*\d)", "strasse", text)
    return re.sub(r"\s+", "", text)


def normalize_unit(value):
    text = normalize_text(value)

    floor_words = {
        "erste": 1,
        "zweite": 2,
        "dritte": 3,
        "vierte": 4,
        "fünfte": 5,
        "sechste": 6,
        "siebte": 7,
        "achte": 8,
        "neunte": 9,
        "zehnte": 10,
    }

    for word, number in floor_words.items():
        text = re.sub(rf"\b{word}[rsn]?\b", str(number), text)

    text = re.sub(
        r"\b(etage|stock|stockwerk|obergeschoss)\b",
        "og",
        text,
    )
    text = re.sub(r"\bli\b", "links", text)
    text = re.sub(r"\bre\b", "rechts", text)

    return re.sub(r"[\s.,]+", "", text)


def review_result(reason, candidates):
    return {
        "status": "needs_review",
        "reason": reason,
        "contract": None,
        "candidates": candidates,
        "previous_cases": [],
    }


def match_contract(tenant_name, address, unit_description):
    if not tenant_name or not address:
        return review_result(
            "The tenant name or address is missing.",
            [],
        )

    with get_connection() as connection:
        contracts = connection.execute(
            """
            SELECT
                contracts.contract_id,
                contracts.tenant_name,
                contracts.unit_id,
                contracts.is_active,
                properties.property_id,
                CONCAT(
                    properties.street, ' ', properties.house_number
                ) AS address,
                units.floor,
                units.side
            FROM inovidus_demo.rental_contracts AS contracts
            JOIN inovidus_demo.units AS units
                ON contracts.unit_id = units.unit_id
            JOIN inovidus_demo.properties AS properties
                ON units.property_id = properties.property_id
            WHERE contracts.is_active = TRUE
            ORDER BY contracts.contract_id
            """
        ).fetchall()

        candidates = [
            contract
            for contract in contracts
            if (
                normalize_text(contract["tenant_name"])
                == normalize_text(tenant_name)
                and normalize_address(contract["address"])
                == normalize_address(address)
            )
        ]

        if not candidates:
            return review_result(
                "No active contract matches the tenant and address.",
                [],
            )

        if unit_description:
            matching_units = [
                contract
                for contract in candidates
                if normalize_unit(
                    f"{contract['floor']}. OG {contract['side']}"
                ) == normalize_unit(unit_description)
            ]

            if not matching_units:
                return review_result(
                    "The supplied apartment details could not be verified.",
                    candidates,
                )

            candidates = matching_units

        if len(candidates) != 1:
            return review_result(
                "Multiple active contracts match. Manual verification is required.",
                candidates,
            )

        contract = candidates[0]

        previous_cases = connection.execute(
            """
            SELECT case_id, title, status
            FROM inovidus_demo.maintenance_cases
            WHERE unit_id = %s
            ORDER BY case_id
            """,
            (contract["unit_id"],),
        ).fetchall()

    return {
        "status": "matched",
        "reason": "Exactly one active contract matches the supplied information.",
        "contract": contract,
        "candidates": candidates,
        "previous_cases": previous_cases,
    }


if __name__ == "__main__":
    complete = match_contract(
        tenant_name="Max Mustermann",
        address="Musterstr. 12",
        unit_description="zweite Etage links",
    )

    print("TEST 1: Complete apartment details")
    print(json.dumps(complete, ensure_ascii=False, indent=2))

    incomplete = match_contract(
        tenant_name="Max Mustermann",
        address="Musterstr. 12",
        unit_description=None,
    )

    print("\nTEST 2: Missing apartment details")
    print(json.dumps(incomplete, ensure_ascii=False, indent=2))