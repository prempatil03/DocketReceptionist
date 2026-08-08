"""Language + emotion engine for the Docket Receptionist.

Two jobs:
  1. detect_language()  — guess the caller's language from their words.
  2. detect_mood()      — guess the caller's tone (angry/confused/impatient/happy).

Every intent has MULTIPLE natural phrasings (`R`), so the bot never sounds
repetitive. The conversation brain rotates through them round-robin and, when
the caller is upset or confused, prepends a mood acknowledgment to sound human.

To edit what the AI says: change the strings in `R` and `ACK` below — no code
knowledge needed, just edit the words. `{company}` and the `{no}/{origin}/...`
placeholders are filled by the code.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------
ENGLISH_MARKERS = [
    "what", "where", "when", "how", "who", "why", "is my", "my parcel",
    "my docket", "the", "please", "thanks", "thank you", "thankyou", "hello",
    "hi", "this", "that", "status", "tell me", "track", "and", "you",
    "not found", "tracking", "delivery", "today", "will", "does", "can",
]

HINDI_MARKERS = [
    "hai", "kya", "batao", "bataiye", "yeh", "mera", "meri", "kahan", "kaha",
    "kaise", "mujhe", "aap", "aapka", "mil", "gaya", "karo", "sirf", "ji",
    "kaun", "kis", "kitna", "kab", "raha", "nhi", "nahi", "chahiye", "diya",
    "bheja", "sala", "sab", "kar", "reh", "ho", "thik", "bata", "de",
]

MARATHI_MARKERS = [
    "ahey", "aahe", "kutey", "kutha", "kuthe", "sang", "sanga", "mala",
    "tula", "kay", "kaay", "kasa", "hey wala", "dya", "zala", "jhalay",
    "mi", "tumcha", "tumhi", "nahi", "ka", "kas", "dila", "ghala", "wala",
]


def detect_language(text: str) -> str:
    """Guess the caller's language from their words. Returns a key for `R`."""
    if not text:
        return "hinglish"
    lower = text.lower()

    def _score(markers: list[str]) -> int:
        return sum(1 for m in markers if m in lower)

    e, h, m = _score(ENGLISH_MARKERS), _score(HINDI_MARKERS), _score(MARATHI_MARKERS)

    # Marathi has very distinctive markers (ahey, kutey, sang, mala) — trust it.
    if m >= 2 and m > e:
        return "marathi"
    if h >= 2 and h > e:
        return "hindi"
    if e >= 2 and e > h and e > m:
        return "english"
    return "hinglish"  # mixed or unclear — the friendly fallback


# ---------------------------------------------------------------------------
# Mood detection
# ---------------------------------------------------------------------------
MOOD_ANGRY = [
    "mkc", "mc", "bc", "bhenchod", "madarchod", "chutiya", "chutiye", "kutte",
    "kuttya", "idiot", "stupid", "fool", "bhag", "chup", "sala", "harami",
    "ghatiya", "dammit", "damn", "shit", "badtameez", "abey", "arre be",
]

MOOD_IMPATIENT = [
    "jaldi", "jaldi karo", "fast", "quick", "asap", "hurry", "abhi", "jao",
    "chalo chalo", "kab tak", "kitna wait", "why late", "late", "delay",
]

MOOD_CONFUSED = [
    "samajh", "nahi aaya", "kya bola", "dubara", "dubara se", "phir se",
    "fir se", "fir se", "kya hua", "pata nahi", "kya karna", "hmm", "huh",
    "confused", "what?", "matlab", "kaise matlab", "bolo kya",
]

MOOD_HAPPY = [
    "thank", "thanks", "dhanyawad", "shukriya", "badhiya", "great", "nice",
    "awesome", "super", "perfect", "good", "bahut accha", "khushi", "maja aaya",
]


def detect_mood(text: str) -> str:
    """Guess the caller's tone. Priority: angry > impatient > confused > happy.

    Short words ("sala", "mc") are matched whole-word so they can't fire inside
    longer words like "salary" — an angry marker must be a real word.
    """
    if not text:
        return "neutral"
    lower = text.lower()

    def _has(markers: list[str]) -> bool:
        for m in markers:
            # Short markers need a word boundary; longer ones are phrases.
            if " " in m or len(m) > 4:
                if m in lower:
                    return True
            elif _word_match(lower, m):
                return True
        return False

    # All-caps shouting is a strong anger signal.
    if _has(MOOD_ANGRY) or (len(text) >= 4 and text.isupper()):
        return "angry"
    if _has(MOOD_IMPATIENT):
        return "impatient"
    if _has(MOOD_CONFUSED):
        return "confused"
    if _has(MOOD_HAPPY):
        return "happy"
    return "neutral"


# ---------------------------------------------------------------------------
# Response templates — every intent has several natural phrasings.
# The brain rotates through them so calls never sound identical.
# ---------------------------------------------------------------------------
R: dict[str, dict[str, list[str]]] = {
    "hinglish": {
        "greeting": [
            "Namaste! {company} mein aapka swagat hai. Main aapki docket tracking mein madad kar sakti hoon. Kripya apna docket number bataye.",
            "Namaste namaste! Yeh {company} hai. Agar aapko apne parcel ki status chahiye to docket number bataiye.",
            "Jai Shree Ram! {company} mein aapka swagat hai. Main yahan docket ki jankari dene ke liye hoon. Aapka docket number kya hai?",
            "Namaste! {company} reception. Main aapke parcel ke baare mein bata sakti hoon. Docket number dijiye.",
        ],
        "ask_number": [
            "Kripya apna docket number bataye. Jaise, 2 3 4 5 8 7.",
            "Docket number kya hai? Jaise 6 digit ka number.",
            "Aapka docket number bataiye, main turant check karti hoon.",
            "Thoda sa docket number dijiye — wo number jo aapke parcel ke saath milta hai.",
        ],
        "not_found": [
            "Sorry ji, yeh docket number nahi mila. Kripya number dobara check karke bataye.",
            "Arre, yeh number humein nahi mila. Aapne sahi number diya hai? Ek baar phir bataiye.",
            "Hmm, yeh docket humare system mein nahi dikh raha. Kripya number verify karke bataye.",
        ],
        "not_found_handoff": [
            "Sorry, yeh docket number hume nahi mil raha hai. Main aapko hamare staff se connect karti hoon.",
            "Kai baar check kiya, phir bhi yeh number nahi mila. Aapka samay bachaane ke liye main aapko hamare team se connect kar deta hoon.",
        ],
        "found": [
            "Ji, aapka docket {no} mil gaya.",
            "Aapka docket {no} mil gaya hai!",
            "{no} — mil gaya.",
        ],
        # Optional clauses — only added when the field has a value.
        "_route_clause": " Route {origin} se {dest}.",
        "_loc_clause": " Abhi yeh {loc} mein hai.",
        "_status_clause": " Status: {status}.",
        "refusal_sensitive": [
            "Sorry ji, yeh information main de nahi sakti. Mujhe sirf docket tracking ki help karni hai. Aap docket number batao, main uska status bata dungi.",
            "Maaf kijiye, yeh baat main nahi bata sakti. Main sirf docket aur parcel ki status batati hoon. Aapka docket number dijiye.",
            "Arre, yeh main nahi bata sakti. Main sirf docket tracking karti hoon. Number batao.",
        ],
        "refusal_jailbreak": [
            "Sorry, main yeh nahi kar sakti. Main sirf docket tracking mein madad karti hoon. Agar aapko apne parcel ki jankari chahiye, to docket number bataye.",
            "Hmm, aisa main nahi kar sakti. Mera kaam sirf docket tracking hai. Docket number dijiye, main madad karti hoon.",
        ],
        "refusal_offtopic": [
            "Sorry ji, yeh mere kaam ka nahi hai. Main sirf docket aur parcel tracking mein help kar sakti hoon. Aap apna docket number bataiye.",
            "Arre, yeh mujhe nahi aati. Main to sirf docket ka status batati hoon. Aapka docket number kya hai?",
            "Achha, wo to main nahi janta. Main sirf parcel tracking mein madad karti hoon. Docket number dijiye.",
        ],
        "thanks": [
            "Aapka swagat hai! Aur kuch madad chahiye?",
            "Koi baat nahi! Aur koi sawaal hai?",
            "Theek hai! Aur kuch puchhna ho to bataiye.",
        ],
        "goodbye": [
            "Call karne ke liye dhanyawad. Aapka din shubh ho. Bye.",
            "Dhanyawad! Aapko acha din ho. Alvida.",
            "Thank you for calling! Goodbye, aapka din shubh ho.",
        ],
        "silence": [
            "Hello? Aap sun rahe hain? Kripya apna docket number bataye.",
            "Hello? Kya aap wahan hain? Docket number batao.",
        ],
        "silence_end": [
            "Mujhe aapki awaz nahi aayi. Call karne ke liye dhanyawad. Bye.",
            "Aapne kuch nahi bola, isliye main call band kar rahi hoon. Dhanyawad, alvida.",
        ],
        "handoff": [
            "Main aapko hamare staff se connect kar rahi hoon. Kripya thodi der ruke.",
        ],
    },
    "hindi": {
        "greeting": [
            "Namaste! {company} mein aapka swagat hai. Main aapki docket tracking mein madad kar sakti hoon. Kripya apna docket number bataye.",
            "Namaste! Yeh {company} hai. Main parcel ki status batane ke liye hoon. Docket number dijiye.",
            "Aadab! {company} mein aapka swagat hai. Kripya apna docket number bataye.",
        ],
        "ask_number": [
            "Kripya apna docket number bataye. Jaise, 2 3 4 5 8 7.",
            "Docket number kya hai?",
            "Apna docket number dijiye, main abhi dekh leti hoon.",
        ],
        "not_found": [
            "Sorry ji, yeh docket number nahi mila. Kripya number dobara check karke bataye.",
            "Arre, yeh number nahi mila. Ek baar phir se bataiye.",
        ],
        "not_found_handoff": [
            "Sorry, yeh docket number nahi mil raha. Main aapko hamare staff se connect karti hoon.",
            "Yeh number hume nahi mila. Aapko hamare team se connect kar deta hoon.",
        ],
        "found": [
            "Ji, aapka docket {no} mil gaya.",
            "Aapka docket {no} mil gaya hai!",
        ],
        "_route_clause": " Route {origin} se {dest}.",
        "_loc_clause": " Abhi yeh {loc} mein hai.",
        "_status_clause": " Status: {status}.",
        "refusal_sensitive": [
            "Sorry ji, yeh jankari main nahi de sakti. Main sirf docket tracking mein madad karti hoon. Aap docket number dijiye, main status bata dungi.",
            "Maaf kijiye, yeh main nahi bata sakti. Main sirf docket ki baat karti hoon. Docket number dijiye.",
        ],
        "refusal_jailbreak": [
            "Sorry, main yeh nahi kar sakti. Main sirf docket tracking mein madad karti hoon. Agar parcel ki jankari chahiye to docket number bataye.",
            "Aisa main nahi kar sakti. Mera kaam sirf docket tracking hai.",
        ],
        "refusal_offtopic": [
            "Sorry ji, yeh mere kaam ka nahi hai. Main sirf docket aur parcel tracking mein help kar sakti hoon. Aap apna docket number bataiye.",
            "Arre, yeh mujhe nahi aati. Main sirf docket ka status batati hoon. Docket number dijiye.",
        ],
        "thanks": [
            "Aapka swagat hai! Aur kuch madad chahiye?",
            "Koi baat nahi! Aur kuch puchhna ho to bataiye.",
        ],
        "goodbye": [
            "Call karne ke liye dhanyawad. Aapka din shubh ho. Alvida.",
            "Dhanyawad! Phir bhi kuch chahiye ho to call kar lena.",
        ],
        "silence": [
            "Hello? Aap sun rahe hain? Kripya docket number bataye.",
            "Hello? Kya aap wahan hain?",
        ],
        "silence_end": [
            "Mujhe aapki awaz nahi aayi. Call karne ke liye dhanyawad. Alvida.",
            "Koi jawab nahi mila, isliye call samapt kar rahi hoon. Dhanyawad.",
        ],
        "handoff": [
            "Main aapko hamare staff se connect kar rahi hoon. Kripya thodi der ruke.",
        ],
    },
    "english": {
        "greeting": [
            "Hello! Welcome to {company}. I can help you track a parcel. Please tell me your docket number.",
            "Good day! This is {company}. Need a parcel status? Just give me the docket number.",
            "Hello, {company} here. I'm happy to check your parcel — what's your docket number?",
        ],
        "ask_number": [
            "Please tell me your docket number. For example, 2 3 4 5 8 7.",
            "What is your docket number?",
            "Could you give me the docket number, please?",
        ],
        "not_found": [
            "Sorry, I could not find that docket number. Please check and tell me again.",
            "Hmm, I couldn't find that one. Did you enter the right number?",
        ],
        "not_found_handoff": [
            "Sorry, I am unable to find that docket number. I am connecting you to our staff.",
            "I've checked a few times but can't find it. Let me connect you to our team.",
        ],
        "found": [
            "Your docket {no} is found.",
            "Found it! Docket {no} is on its way.",
        ],
        "_route_clause": " Route {origin} to {dest}.",
        "_loc_clause": " It is currently at {loc}.",
        "_status_clause": " Status: {status}.",
        "refusal_sensitive": [
            "Sorry, I cannot share that information. I only help with docket tracking. Please give me your docket number and I will tell you its status.",
            "I'm afraid I can't reveal that. I only assist with parcel tracking. Could you give me your docket number?",
        ],
        "refusal_jailbreak": [
            "Sorry, I cannot do that. I only help with docket tracking. If you need parcel information, please give me your docket number.",
            "I can't do that, I'm afraid. My job is only docket tracking.",
        ],
        "refusal_offtopic": [
            "Sorry, that is not something I can help with. I only assist with docket and parcel tracking. Please give me your docket number.",
            "That's outside what I do. I only track parcels — what's your docket number?",
        ],
        "thanks": [
            "You're welcome! Is there anything else I can help you with?",
            "Happy to help! Anything else?",
        ],
        "goodbye": [
            "Thank you for calling. Have a nice day! Goodbye.",
            "Thanks for reaching out. Take care, goodbye!",
        ],
        "silence": [
            "Hello? Are you still there? Please tell me your docket number.",
            "Hello? Can you hear me?",
        ],
        "silence_end": [
            "I could not hear you. Thank you for calling. Goodbye.",
            "I didn't get a response, so I'll end this call. Thank you, goodbye.",
        ],
        "handoff": [
            "I am connecting you to our staff. Please hold on.",
        ],
    },
    "marathi": {
        "greeting": [
            "Namaskar! {company} madhe swagat. Mi tumcha docket tracking madhe madat karu shakte. Kripya tumcha docket number sanga.",
            "Namaskar! He {company} aahe. Parcel chi status hovya karata docket number sanga.",
        ],
        "ask_number": [
            "Kripya tumcha docket number sanga. Udaharanarath, 2 3 4 5 8 7.",
            "Tumcha docket number kay aahe?",
            "Docket number dya, mi aata baghate.",
        ],
        "not_found": [
            "Maaf kara, he docket number sapadle nahi. Kripya number parat tarun sanga.",
            "Arre, ha number sapadla nahi. Parat ekda sanga.",
        ],
        "not_found_handoff": [
            "Maaf kara, he docket number sapadle nahi. Mi tumhala amachya staff kade connect karte.",
            "Ha number sapadla nahi. Tumhala amachya team kade connect karte.",
        ],
        "found": [
            "Ho ji, tumcha docket {no} sapadle.",
            "Sapadle! Tumcha docket {no} sapadla.",
        ],
        "_route_clause": " Route {origin} to {dest}.",
        "_loc_clause": " He aata {loc} la aahe.",
        "_status_clause": " Status: {status}.",
        "refusal_sensitive": [
            "Maaf kara, he mahiti mi deu shakat nahi. Mi fakt docket tracking madhe madat karte. Tumcha docket number dya, mi status sangte.",
            "Maaf kara, he sangta yet nahi. Mi fakt docket chi baat karte. Docket number sanga.",
        ],
        "refusal_jailbreak": [
            "Maaf kara, mi he karu shakat nahi. Mi fakt docket tracking madhe madat karte. Parcel chi mahiti asel tar docket number sanga.",
            "He mi karu shakat nahi. Maza kaam fakt docket tracking aahe.",
        ],
        "refusal_offtopic": [
            "Maaf kara, he maza kaam nahi. Mi fakt docket ani parcel tracking madhe madat karu shakte. Tumcha docket number sanga.",
            "Arre, he mala yet nahi. Mi fakt docket chi status sangte. Tumcha docket number kay aahe?",
        ],
        "thanks": [
            "Tumcha swagat! Aanik kahi madat havya ka?",
            "Kahi nahi! Aanik kahi puchaycha asel tar sanga.",
        ],
        "goodbye": [
            "Call karanyabaddal dhanyawad. Tumcha divas shubh jao. Aani bhetu.",
            "Dhanyawad! Aanik kahi hava asel tar call karra.",
        ],
        "silence": [
            "Hello? Tumhi aikta aahat ka? Kripya docket number sanga.",
            "Hello? Tumhi thet aahat ka?",
        ],
        "silence_end": [
            "Tumchi awaj aikayla aali nahi. Call karanyabaddal dhanyawad. Aani bhetu.",
            "Uttar aala nahi, mhanun call band karatoy. Dhanyawad.",
        ],
        "handoff": [
            "Mi tumhala amachya staff kade connect karte. Kripya thamba.",
        ],
    },
}

# ---------------------------------------------------------------------------
# Mood acknowledgments — prepended to refusals / not-found / prompts so an
# upset or confused caller feels heard before we redirect them.
# ---------------------------------------------------------------------------
ACK: dict[str, dict[str, list[str]]] = {
    "angry": {
        "hinglish": ["Arre, main samajh gayi. Gusse mein nahi, main aapki madat karti hoon. ", "Pareshan hona theek hai. Mujhe maaf kijiye, main turant dekhta hoon. "],
        "hindi": ["Main samajh gayi. Gusse mein nahi, main madat karti hoon. ", "Maaf kijiye, main turant dekh leti hoon. "],
        "english": ["I understand, I'm sorry about that. Let me help. ", "I hear you, and I'm sorry. Let me fix this. "],
        "marathi": ["Mi samjun ghetle. Gaam khau nako, mi madat karte. ", "Maaf kara, mi lavkar baghate. "],
    },
    "impatient": {
        "hinglish": ["Theek hai theek hai, jaldi karte hain. ", "Bas ek second, main check karti hoon. ", "Tension mat lo, abhi batati hoon. "],
        "hindi": ["Jaldi karte hain. ", "Ek minute, main dekh leti hoon. "],
        "english": ["Right away — let me check. ", "One moment, I'll look that up. "],
        "marathi": ["Lavkar karte. ", "Ek sekand, mi baghate. "],
    },
    "confused": {
        "hinglish": ["Koi baat nahi, main samjhati hoon. ", "Chinta mat karo, main dobara saaf-saaf batati hoon. ", "Samajhne mein dikkat ho rahi hai? Main saaf batati hoon. "],
        "hindi": ["Koi baat nahi, main samjhati hoon. ", "Chinta mat karo, dobara batati hoon. "],
        "english": ["No problem, let me explain. ", "Don't worry, I'll say it again clearly. "],
        "marathi": ["Kashi nahi, mi samjavte. ", "Kavala nako, mi parat sangte. "],
    },
    "happy": {
        "hinglish": ["Bahut badhiya! ", "Wah, acha sunke khushi hui! ", "Aapko madad mili, isse khushi hui! "],
        "hindi": ["Bahut badhiya! ", "Acha sunke khushi hui. "],
        "english": ["Wonderful! ", "Great to hear! ", "So glad to help! "],
        "marathi": ["Khup chaan! ", "Achhe aikatun aanand zala! "],
    },
}

# Intents that should carry a mood acknowledgment. "found" stays clean/factual.
ACK_APPLIES = {
    "refusal_sensitive", "refusal_jailbreak", "refusal_offtopic",
    "not_found", "not_found_handoff", "ask_number", "silence", "silence_end",
}


# ---------------------------------------------------------------------------
# Polite intent detection (thanks / goodbye / greeting)
# ---------------------------------------------------------------------------
THANKS_WORDS = ["thank", "thanks", "thnx", "thx", "shukriya", "dhanyawad", "theek hai", "ok", "okay", "got it"]

# Phrases that mean "I'm leaving / ending this" — these MUST end the call.
# Phrase keys are substring-matched; single-word keys are whole-word matched.
GOODBYE_PHRASES = [
    "bye", "goodbye", "good bye", "bye bye", "alvida", "aani bhetu",
    "bhetu", "nko", "take care", "see you", "jata hoon", "ja raha",
    "ja rahe", "chalte hai", "chalte hain", "chalte hey", "chale",
    "chalo", "chala",
    "i am done", "i am leaving", "i am going", "im leaving", "im going",
    "got to go", "gotta go", "end the call", "bas", "chalta hoon",
    "dismiss", "leaving now", "going now", "going home", "jaata hoon",
]
# Short "no, I'm done" endings — only count when the message is VERY short,
# so "nai samajh nahi aaya" (confused, not leaving) isn't misread as goodbye.
NO_MORE_PHRASES = ["nai", "nahi", "no", "nothing", "that's all", "bas", "ho gaya", "ho gya", "done"]
NO_MORE_MAX_WORDS = 2

GREETING_WORDS = ["hello", "hi", "namaste", "namaskar", "good morning", "good afternoon", "good evening", "hey"]


def _word_match(text_lower: str, word: str) -> bool:
    """Whole-word match. 'hi' must be a real word, not a piece of 'chahiye'."""
    return re.search(rf"(?<![a-z]){re.escape(word)}(?![a-z])", text_lower) is not None


def intent_of(text: str) -> str | None:
    """Classify polite speech (thanks/goodbye/greeting). Returns intent or None."""
    lower = text.lower()

    # 1) Goodbye — caller is leaving. Highest priority; ends the call.
    #    Multi-word phrases use substring match; single words need word match.
    if any(p in lower for p in GOODBYE_PHRASES if " " in p or len(p) > 4) or \
       any(_word_match(lower, p) for p in GOODBYE_PHRASES if " " not in p and len(p) <= 4):
        return "goodbye"

    # 2) Short "no more / I'm done" answer -> also a goodbye.
    word_count = len(text.split())
    if word_count <= NO_MORE_MAX_WORDS and \
       any(_word_match(lower, p) for p in NO_MORE_PHRASES):
        return "goodbye"

    # 3) Thanks (can come embedded: "ok thankyou", "got it thanks").
    if any(w in lower for w in THANKS_WORDS if len(w) > 2) or \
       any(_word_match(lower, w) for w in THANKS_WORDS if len(w) <= 2):
        return "thanks"

    # 4) Greeting.
    if any(_word_match(lower, w) for w in GREETING_WORDS):
        return "greeting"

    return None
