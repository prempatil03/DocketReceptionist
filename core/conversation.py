"""The conversation brain of the Docket Receptionist.

Flow:
  greet -> ask for docket number -> lookup in store -> reply with status
  sensitive / jailbreak / off-topic -> polite refusal + redirect back
  thanks / goodbye / greeting -> polite, natural replies

The AI replies in the SAME language the caller speaks (english/hindi/marathi/
hinglish), and its TONE adapts to the caller's mood (angry/impatient/confused/
happy). Reply phrasing rotates so no two calls sound identical.

It NEVER outputs anything from the data source except the allowed fields on
DocketRecord. Everything is passed through the guardrails first.
"""

from __future__ import annotations

from dataclasses import dataclass

from config.settings import COMPANY_NAME, MAX_DOCKET_ATTEMPTS
from core.docket_store import DocketRecord, DocketStore, get_docket_store
from core.guardrails import Topic, classify
from core.language import R, ACK, ACK_APPLIES, detect_language, detect_mood


@dataclass
class Reply:
    text: str                       # what the AI says out loud
    transfer_to_human: bool = False # offer a human if True
    hangup: bool = False            # end the call if True


class Receptionist:
    def __init__(self, store: DocketStore | None = None, company: str = COMPANY_NAME):
        self.store = store or get_docket_store()
        self.company = company
        self.missed_attempts = 0     # failed docket lookups in this call
        self.docket_asked = False    # have we already asked for the number?
        self.silences = 0            # consecutive no-response timeouts
        self._current_lang = "hinglish"
        self._variant_ix: dict[str, int] = {}  # round-robin position per intent

    # -- public API ----------------------------------------------------------
    def start(self) -> str:
        """First thing spoken when the call is answered (Hinglish default)."""
        return self._say("greeting")

    def respond(self, caller_text: str) -> Reply:
        """Handle one thing the caller said. Returns what the AI says."""
        # A real response means the caller IS there — reset silence counter.
        if caller_text and caller_text.strip():
            self.silences = 0

        result = classify(caller_text)
        lang = detect_language(caller_text)
        mood = detect_mood(caller_text)
        self._current_lang = lang

        # 1) Blocked topics: refuse firmly, redirect back to docket.
        if result.topic in (Topic.SENSITIVE, Topic.JAILBREAK, Topic.OFF_TOPIC):
            self.missed_attempts += 1
            # NOTE: template keys use "offtopic" (no underscore) — map them.
            refusal_key = "refusal_offtopic" if result.topic == Topic.OFF_TOPIC \
                          else "refusal_" + result.topic.name.lower()
            text = self._say(refusal_key, lang, mood)
            if self.missed_attempts >= MAX_DOCKET_ATTEMPTS:
                self.missed_attempts = 0  # reset after handoff — don't re-handoff
                return Reply(text, transfer_to_human=True)
            return Reply(text)

        # 2) Polite speech — never treat "ok thankyou" as off-topic.
        if result.topic == Topic.THANKS:
            return Reply(self._say("thanks", lang, mood))
        if result.topic == Topic.GOODBYE:
            return Reply(self._say("goodbye", lang, mood), hangup=True)
        if result.topic == Topic.GREETING:
            return Reply(self._say("greeting", lang, mood))

        # 3) Legitimate docket request.
        if result.topic == Topic.DOCKET:
            return self._handle_docket(result.docket_number, lang, mood)

        # 4) Should be unreachable (classify always returns a topic).
        return Reply(self._say("refusal_offtopic", lang, mood))

    def silence(self) -> Reply:
        """Caller said nothing for a while — ask once, then end politely."""
        self.silences += 1
        if self.silences >= 2:
            return Reply(self._say("silence_end", self._current_lang), hangup=True)
        return Reply(self._say("silence", self._current_lang))

    # -- internals -------------------------------------------------------------
    def _pick(self, key: str, lang: str) -> str:
        """Pick the next natural phrasing for an intent (round-robin)."""
        variants = R.get(lang, R["hinglish"]).get(key)
        if not variants:
            variants = R["hinglish"].get(key) or ["Kripya apna docket number bataye."]
        ix = self._variant_ix.get(key, 0) % len(variants)
        self._variant_ix[key] = ix + 1
        return variants[ix]

    def _say(self, key: str, lang: str = "hinglish", mood: str = "neutral") -> str:
        """Build a reply: acknowledgment (if mood) + natural phrasing.

        Never returns an empty string — falls back to Hinglish, then a safe line.
        """
        text = self._pick(key, lang).replace("{company}", self.company)

        if mood != "neutral" and key in ACK_APPLIES:
            acks = ACK.get(mood, {}).get(lang) or ACK.get(mood, {}).get("hinglish") or []
            if acks:
                ack = acks[self._variant_ix.get("_ack", 0) % len(acks)]
                self._variant_ix["_ack"] = self._variant_ix.get("_ack", 0) + 1
                text = ack + text

        return text

    def _handle_docket(self, docket_number: str | None, lang: str, mood: str) -> Reply:
        # Caller didn't say a number yet (just said "status"/"track") -> ask.
        if not docket_number:
            self.docket_asked = True
            return Reply(self._say("ask_number", lang, mood))

        record = self.store.lookup(docket_number)

        if record is not None:
            self.missed_attempts = 0  # success resets the frustration counter
            return Reply(self._format_found(record, lang, mood))

        # Not found.
        self.missed_attempts += 1
        if self.missed_attempts >= MAX_DOCKET_ATTEMPTS:
            return Reply(self._say("not_found_handoff", lang, mood), transfer_to_human=True)
        return Reply(self._say("not_found", lang, mood))

    def _format_found(self, record: DocketRecord, lang: str, mood: str) -> str:
        """Turn the allowed fields into words, in the caller's language.

        The found-reply stays factual; only a happy mood gets a light cheer.
        Clauses with no data (empty location) are SKIPPED, never spoken blank.
        """
        template = self._pick("found", lang)
        text = template.replace("{no}", record.docket_number)

        # Route is optional — only add it when the DB has it.
        if record.origin and record.destination:
            route_clause = R.get(lang, R["hinglish"]).get("_route_clause", "")
            text += route_clause.replace("{origin}", record.origin) \
                                .replace("{dest}", record.destination)

        # Location is optional — only add it when the DB actually has one.
        if record.location:
            loc_clause = R.get(lang, R["hinglish"]).get("_loc_clause", "")
            text += loc_clause.replace("{loc}", record.location)

        # Status is optional too.
        if record.status:
            status_clause = R.get(lang, R["hinglish"]).get("_status_clause", "")
            text += status_clause.replace("{status}", record.status)

        if mood == "happy":
            acks = ACK.get("happy", {}).get(lang) or ACK.get("happy", {}).get("hinglish") or []
            if acks:
                text = acks[0] + text
        return text
