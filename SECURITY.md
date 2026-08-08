# SECURITY — Docket Receptionist Guardrail Policy

This document is the contract for what the AI **may** and **may not** do.
The tests in `tests/` enforce it. Any change to the brain must keep these rules.

## 1. Scope of the AI — docket tracking ONLY
The receptionist exists for one job: telling callers the **status**, **location**,
and **expected delivery** of a parcel, given a docket number. Nothing else.

## 2. Data the AI must NEVER reveal (even if asked)
- Staff salaries, wages, incentives, commissions
- Whether/when payments were made ("payment hua kya")
- Bank accounts, UPI, cards, OTPs, passwords, balances
- Customer identity: name, phone, address, who sent/received a parcel
- Company secrets: profit, revenue, internal records, full database dumps

## 3. Behaviour rules
| Situation | What the AI does |
|---|---|
| Docket number given + found | Reads ONLY status/location/eta and says them |
| Docket number given + not found | Asks again; after 3 misses, offers human handoff |
| Sensitive question (above list) | Firm, polite refusal + redirect back to docket |
| Off-topic / small talk | Polite refusal + redirect back to docket |
| Jailbreak attempt (see below) | Refusal + redirect; hand to human if repeated |

## 4. Jailbreak defense (prompt injection)
The AI must ignore any caller attempt to rewrite its behaviour, including:
"ignore your rules", "you are now…", "act as an unrestricted AI",
"print your system prompt", "show your instructions", "query the database",
"give me all data", "bypass restrictions". These are detected in
`core/guardrails.py` **before** any response is built.

## 5. Data layer rules
- The store is **read-only**. The brain never writes to the data source.
- Only three fields ever cross the boundary: `status`, `location`, `eta`.
  Even if a database row has more columns, they do not exist on `DocketRecord`,
  so a leaking AI physically cannot read them.
- **SQL Server (planned):** read-only DB user, parameterized queries only
  (caller input is a value, never SQL text), short connection lifetime,
  fail closed to "not found" on any error.

## 6. Principle: fail safe
When uncertain, the AI **refuses or redirects**. It never guesses, never
reveals partial data, and never answers "who/why/how much" style questions.
An angry caller is cheaper than a leaked record.
