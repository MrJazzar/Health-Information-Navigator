"""Transparent safety and scope routing before retrieval or generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class Route(str, Enum):
    NORMAL = "normal"
    URGENT_SUPPORT = "urgent_support"
    PROFESSIONAL_SUPPORT = "professional_support"
    PRIVACY_PROTECTION = "privacy_protection"
    LOCAL_EMERGENCY_INFORMATION = "local_emergency_information"


@dataclass(frozen=True)
class SafetyDecision:
    route: Route
    response: str | None = None


_URGENT_PATTERNS = (
    re.compile(
        r"\b(i|i'm|i am|i've|i have)\b.{0,55}\b("
        r"kill(?:ing)? myself|hurt(?:ing)? myself|harm(?:ing)? myself|end my life|suicid(?:e|al)|"
        r"not want to live|want to die|wish i (?:was|were) dead|"
        r"thinking about ending my life|planning to (?:kill myself|end my life)|"
        r"can't keep myself safe|cannot keep myself safe)\b",
        re.I,
    ),
    re.compile(
        r"\b(i|someone|my friend|they|he|she)\b.{0,55}\b"
        r"(?:might|may|will|plan to|planning to|going to)\s+"
        r"(?:kill|hurt|harm)\s+(?:someone|another person|myself|themself|themselves)\b",
        re.I,
    ),
    re.compile(
        r"\b(i|someone|they|he|she)\b.{0,55}\b("
        r"going to (?:kill|hurt|harm)|about to (?:kill|hurt|harm)|"
        r"has a plan to (?:kill|hurt|harm))\b",
        re.I,
    ),
    re.compile(
        r"\b(immediate danger|in immediate danger|about to hurt (?:someone|another person))\b",
        re.I,
    ),
)
_PROFESSIONAL_PATTERNS = (
    re.compile(r"\b(do i have|diagnose me with|am i suffering from)\b", re.I),
    re.compile(
        r"\b(which medication|what medication|medication dosage|"
        r"(?:what|which|how much|exact)\s+(?:dose|dosage)|"
        r"\d+\s*(?:mg|milligrams?)|should i take .* medication)\b",
        re.I,
    ),
    re.compile(
        r"\b(tell me what treatment|what treatment should i|recommend .* treatment|"
        r"prescribe|treatment plan for me)\b",
        re.I,
    ),
)
_PRIVACY_PATTERNS = (
    re.compile(
        r"\b(?:tell me|find|look up|retrieve|access|show me|share)\b.{0,80}\b"
        r"(?:private|medical|mental health|counsel(?:ing|ling)|therapy|health)\b"
        r".{0,40}\b(?:records?|file|history|notes?)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:what is|tell me|find out)\b.{0,50}\b"
        r"(?:my roommate|my classmate|my friend|another student)'?s?\b.{0,40}\b"
        r"(?:diagnosis|medication|counsel(?:ing|ling)|therapy|health)\b",
        re.I,
    ),
)
_LOCAL_EMERGENCY_PATTERNS = (
    re.compile(
        r"\b(?:what|which)\b.{0,45}\b(?:emergency number|number for emergency|"
        r"number should i call|emergency phone number)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:emergency number|emergency services number)\b.{0,45}\b"
        r"(?:my country|my location|where i live|here)\b",
        re.I,
    ),
)

URGENT_RESPONSE = (
    "I’m sorry you’re facing this. This tool cannot provide emergency help. If you or "
    "someone else may be in immediate danger, contact your local emergency services now "
    "or go to a nearby emergency department. If you can, tell a trusted person nearby "
    "and ask them to stay with you while you get help. I do not monitor this chat or "
    "contact services for you."
)
PROFESSIONAL_RESPONSE = (
    "I can share general educational information, but I can’t diagnose, recommend "
    "medication, or create a treatment plan. A qualified health professional can help "
    "with advice for your situation."
)
PRIVACY_RESPONSE = (
    "I can’t access or disclose another person’s private health information. Please "
    "avoid sharing identifying or confidential details here. If you want general "
    "guidance on supporting someone, ask without names or personal records."
)
LOCAL_EMERGENCY_INFORMATION_RESPONSE = (
    "Emergency numbers depend on your location, which this tool does not know. Check "
    "your local government's or emergency service's official information. If someone "
    "may be in immediate danger now, contact local emergency services or go to a nearby "
    "emergency department. This tool cannot dispatch help."
)


def assess_question(question: str) -> SafetyDecision:
    for pattern in _URGENT_PATTERNS:
        if pattern.search(question):
            return SafetyDecision(Route.URGENT_SUPPORT, URGENT_RESPONSE)
    for pattern in _LOCAL_EMERGENCY_PATTERNS:
        if pattern.search(question):
            return SafetyDecision(
                Route.LOCAL_EMERGENCY_INFORMATION,
                LOCAL_EMERGENCY_INFORMATION_RESPONSE,
            )
    for pattern in _PRIVACY_PATTERNS:
        if pattern.search(question):
            return SafetyDecision(Route.PRIVACY_PROTECTION, PRIVACY_RESPONSE)
    for pattern in _PROFESSIONAL_PATTERNS:
        if pattern.search(question):
            return SafetyDecision(Route.PROFESSIONAL_SUPPORT, PROFESSIONAL_RESPONSE)
    return SafetyDecision(Route.NORMAL)
