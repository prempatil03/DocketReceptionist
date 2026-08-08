"""Guardrails — the security shield of the receptionist.

The AI is ONLY allowed to talk about docket/parcel tracking. Anything else
is handled with a polite, firm refusal. This module decides that for us
BEFORE the conversation brain answers, so a caller can never steer the AI
into revealing data (salary, payments, customer details, etc.).

Categories a caller's message can be classified as:
  * DOCKET       -> a legitimate docket-tracking request
  * SENSITIVE    -> asks about data we must never give (salary, payment,
                    customer personal info, bank, identity...)
  * JAILBREAK    -> tries to hack the AI itself (ignore your rules, act as...)
  * OFF_TOPIC    -> small talk / anything unrelated to tracking
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto

from config.settings import MAX_INPUT_LENGTH
from core.language import intent_of


class Topic(Enum):
    DOCKET = auto()
    SENSITIVE = auto()
    JAILBREAK = auto()
    OFF_TOPIC = auto()
    GREETING = auto()
    THANKS = auto()
    GOODBYE = auto()


@dataclass(frozen=True)
class Classification:
    topic: Topic
    docket_number: str | None = None  # digits found in a DOCKET message


# --- Keyword lists (Hinglish + Hindi + English) --------------------------------
# Data we must NEVER reveal to a caller.
SENSITIVE_KEYWORDS = [
    # salary / staff payments
    "salary", "veta", "inam", "commission", "kamai", "kamayi",
    "paid", "payment", "pay", "tanka", "invoice", "bill", "billing",
    "paisa", "paisa pay", "cash", "bank", "banking", "account", "upi",
    "balance", "credits", "money", "dhan", "roka", "transfer",
    "paid kya", "payment hua", "salary mila", "salary kitna",
    # personal / private info
    "customer number", "customer ka number", "customer ki number", "customer phone",
    "customer numbere", "customer mobile", "customer mibile", "custoemr", "cust oemr",
    "number do", "phone no", "phone number", "mibile number", "mobile number",
    "address", "pata", "ghar", "home address", "aadhaar", "aadhar", "pan number",
    "pan card", "passport", "id proof", "identity", "password", "otp", "pin",
    "account number", "card number", "name of customer", "kiska",
    "ko aaya", "kisne bheja", "sender", "receiver name", "receiver ka",
    # identity questions ("who...") — anyone asking WHO must be refused
    "kisne", "kaun", "kiske", "kiski", "kon", "kaun hai", "kisne diya",
    "kisne bheja", "kisne paisa", "kiske paas", "kiske liye", "kiske naam",
    # company secrets
    "profit", "loss", "revenue", "turnover", "margin", "internal", "secret",
    "sab data", "pura data", "all data", "database", "table", "records",
]

# Phrases callers use to try to hack the AI (prompt injection / jailbreak).
JAILBREAK_KEYWORDS = [
    "ignore", "ignore your rules", "ignore previous", "forget your", "forget all",
    "you are now", "act as", "pretend to be", "system prompt", "system prompt ko",
    "developer message", "reveal your", "tell me your rules", "what are your rules",
    "show instructions", "print instructions", "access log", "source code",
    "read the file", "read database", "query the database", "run sql", "execute",
    "give me all", "everything about", "dump", "raw data", "hidden",
    "no restrictions", "unlimited", "break the rules", "override", "bypass",
]

# Words that signal a docket/parcel tracking request.
DOCKET_KEYWORDS = [
    "docket", "parcel", "courier", "package", "shipment", "consignment",
    "track", "tracking", "status", "kahan", "kaha", "kidhar", "kitna time",
    "arrive", "aayega", "aa gaya", "delivered", "delivery", "pahunch",
    "recieve", "received", "pakad", "karib", "station", "hub",
]


def _has_any(text_lower: str, keywords: list[str]) -> bool:
    """Keyword match with word-boundary awareness for short english words."""
    for kw in keywords:
        if kw in text_lower:
            return True
    return False


def extract_docket_number(text: str) -> str | None:
    """Find a likely docket number: a run of 6–14 digits.

    Digits can be glued to letters ("56600991jaldii" still finds 56600991),
    but must not be part of a longer digit run.
    """
    matches = re.findall(r"(?<!\d)\d{6,14}(?!\d)", text)
    return matches[0] if matches else None


def classify(text: str) -> Classification:
    """Classify a caller's message. Always returns something safe to act on."""
    if not text or len(text) > MAX_INPUT_LENGTH:
        # Empty/over-long input -> treat as off-topic; never answer.
        return Classification(Topic.OFF_TOPIC)

    lower = text.lower()

    # 1) Hard rule: jailbreak attempts are refused FIRST (highest priority).
    if _has_any(lower, JAILBREAK_KEYWORDS):
        return Classification(Topic.JAILBREAK)

    # 2) Sensitive topics are refused before anything else.
    if _has_any(lower, SENSITIVE_KEYWORDS):
        return Classification(Topic.SENSITIVE)

    # 3) Legitimate docket request — try to pull the number out.
    if _has_any(lower, DOCKET_KEYWORDS) or extract_docket_number(text):
        return Classification(Topic.DOCKET, docket_number=extract_docket_number(text))

    # 4) Polite speech: greeting / thanks / goodbye.
    intent = intent_of(text)
    if intent == "thanks":
        return Classification(Topic.THANKS)
    if intent == "goodbye":
        return Classification(Topic.GOODBYE)
    if intent == "greeting":
        return Classification(Topic.GREETING)

    # 5) Anything else is off-topic.
    return Classification(Topic.OFF_TOPIC)


# ----------------------------------------------------------------------------
# Refusal replies — firm, polite, human-sounding. Never reveal anything.
# ----------------------------------------------------------------------------

REFUSALS = {
    Topic.SENSITIVE: (
        "Sorry ji, yeh information main de nahi sakta. "
        "Mujhe sirf docket tracking ki help karni hai. "
        "Aap docket number batao, main uska status bata dunga."
    ),
    Topic.JAILBREAK: (
        "Sorry, main yeh nahi kar sakta. "
        "Main sirf docket tracking mein madad karta hoon. "
        "Agar aapko apne parcel ki jankari chahiye, to docket number bataye."
    ),
    Topic.OFF_TOPIC: (
        "Sorry ji, yeh mere kaam ka nahi hai. "
        "Main sirf docket aur parcel tracking mein help kar sakta hoon. "
        "Aap apna docket number bataiye."
    ),
}


def refusal_for(topic: Topic) -> str:
    return REFUSALS.get(topic, REFUSALS[Topic.OFF_TOPIC])
