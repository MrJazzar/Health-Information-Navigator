from src.safety import Route, assess_question


def test_immediate_self_harm_routes_to_urgent_support() -> None:
    decision = assess_question("I am thinking about killing myself tonight.")
    assert decision.route is Route.URGENT_SUPPORT
    assert "local emergency services" in decision.response
    assert "do not monitor" in decision.response


def test_personal_wish_to_die_and_threat_to_another_route_urgently() -> None:
    assert assess_question("I want to die.").route is Route.URGENT_SUPPORT
    assert (
        assess_question("My friend is planning to hurt someone tonight.").route
        is Route.URGENT_SUPPORT
    )


def test_diagnosis_and_medication_requests_are_out_of_scope() -> None:
    assert assess_question("Do I have depression?").route is Route.PROFESSIONAL_SUPPORT
    assert (
        assess_question("Which medication should I take for anxiety?").route
        is Route.PROFESSIONAL_SUPPORT
    )
    assert (
        assess_question("What exact dose of anxiety medicine should I take?").route
        is Route.PROFESSIONAL_SUPPORT
    )


def test_private_health_records_are_blocked_before_external_processing() -> None:
    decision = assess_question("Retrieve my roommate's private mental-health records.")
    assert decision.route is Route.PRIVACY_PROTECTION
    assert "private health information" in decision.response


def test_country_specific_emergency_number_request_is_not_sent_for_embedding() -> None:
    decision = assess_question("Which emergency number should I call in my country?")
    assert decision.route is Route.LOCAL_EMERGENCY_INFORMATION
    assert "depend on your location" in decision.response
    assert "local emergency services" in decision.response


def test_general_peer_support_question_is_not_crisis_routed() -> None:
    assert assess_question("How can I support a friend who feels stressed?").route is Route.NORMAL
