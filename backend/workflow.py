import json

from erp import match_contract


def assess_urgency(report):
    if report["ongoing_leak"] is True:
        reason = "Ein laufender Wasseraustritt wurde gemeldet."

        if report["property_damage_reported"] is True:
            reason += " Zusätzlich wird bereits ein Sachschaden gemeldet."

        return {
            "level": "high",
            "reason": reason,
        }

    return {
        "level": "needs_review",
        "reason": "Die Dringlichkeit muss fachlich bewertet werden.",
    }


def build_workflow(report, erp_match, subject):
    urgency = assess_urgency(report)

    reply_parts = [
        "Guten Tag,",
        "vielen Dank für Ihre Schadenmeldung.",
    ]

    if erp_match["status"] == "matched":
        contract = erp_match["contract"]

        task = {
            "status": "proposed",
            "type": "maintenance_review",
            "priority": urgency["level"],
            "title": "Schadenmeldung fachlich prüfen",
            "description": report["damage_summary"],
            "contract_id": contract["contract_id"],
            "property_id": contract["property_id"],
            "unit_id": contract["unit_id"],
            "related_cases": erp_match["previous_cases"],
        }

    else:
        if erp_match["candidates"]:
            clarification = (
                "Bitte bestätigen Sie die Etage und die Lage Ihrer Wohnung "
                "(zum Beispiel links oder rechts), damit wir Ihre Meldung "
                "eindeutig zuordnen können."
            )
        else:
            clarification = (
                "Bitte bestätigen Sie Ihren vollständigen Namen, die Adresse "
                "mit Hausnummer sowie die Etage und Lage Ihrer Wohnung, "
                "damit wir Ihre Meldung zuordnen können."
            )

        reply_parts.append(clarification)

        task = {
            "status": "proposed",
            "type": "verify_assignment",
            "priority": urgency["level"],
            "title": "Zuordnung der Schadenmeldung prüfen",
            "description": report["damage_summary"],
            "contract_id": None,
            "property_id": None,
            "unit_id": None,
            "related_cases": [],
        }

    if urgency["level"] == "high":
        reply_parts.append(
            "Wir haben Ihre Meldung als dringlich eingestuft."
        )

    reply_parts.extend([
        "Falls Fotos vorliegen, fügen Sie diese bitte Ihrer Antwort bei.",
        "Wir melden uns bei Ihnen zu den nächsten Schritten.",
        "Mit freundlichen Grüßen",
    ])

    return {
        "urgency": urgency,
        "tenant_reply": {
            "status": "draft",
            "requires_human_review": True,
            "subject": "Re: " + subject,
            "body": "\n\n".join(reply_parts),
        },
        "internal_task": task,
    }


if __name__ == "__main__":
    subject = "Wasserschaden Küche, Musterstraße 12"

    report = {
        "damage_summary": (
            "Wasser läuft unter der Küchenspüle aus. "
            "Der Küchenunterschrank ist aufgequollen."
        ),
        "ongoing_leak": True,
        "property_damage_reported": True,
    }

    matched = match_contract(
        tenant_name="Max Mustermann",
        address="Musterstr. 12",
        unit_description="zweite Etage links",
    )

    complete_result = build_workflow(
        report=report,
        erp_match=matched,
        subject=subject,
    )

    print("TEST 1: Verified apartment")
    print(json.dumps(complete_result, ensure_ascii=False, indent=2))

    ambiguous = match_contract(
        tenant_name="Max Mustermann",
        address="Musterstr. 12",
        unit_description=None,
    )

    review_result = build_workflow(
        report=report,
        erp_match=ambiguous,
        subject=subject,
    )

    print("\nTEST 2: Apartment needs verification")
    print(json.dumps(review_result, ensure_ascii=False, indent=2))