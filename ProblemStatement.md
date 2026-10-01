# Problem Statement — MVP
## OCR-Based Document Search for Google Photos

## Context
This MVP follows directly from validated research: a discovery engine (1200+ items
analyzed), a 35-person survey (24 active Google Photos users), 4 structured user
interviews, and direct hands-on testing of Google Photos' live search feature
(Ask Photos).

## The Problem (Confirmed Root Cause)
Users regularly need to retrieve document-type images — Aadhaar cards, mark sheets,
payment screenshots, medicine labels, job posting screenshots — but Google Photos'
search fails to find them, even when the user's memory is precise (not vague).

Direct testing proved this is NOT a "vague memory" problem for this segment:
- Searching "Samrat Mehta Aadhaar" (exact name) → zero results
- Searching "Aadhaar" alone → a pile of unrelated ID cards; the correct one only
  appeared because the person's face was already tagged in the library — not
  because the system read the name printed on the card
- Searching an untagged name ("Shanti") → returned unrelated temple/religious
  photos, because the system fell back to word-association on the word's meaning
- Searching "payment 6500" (exact amount) → returned 6000, 5000, 1500 — never
  the correct amount
- Searching "invoice" → returned mark sheets, checkbooks, prescriptions — matched
  on "this looks like a paper document" as a visual category, not on any text

**Confirmed root cause:** Google Photos' search relies on face recognition and
broad visual/scene categorization. It does not read or index the actual text,
numbers, or names printed inside a document-type image. A document is only
findable by coincidence (a tagged face, or a generically evocative word) —
never because the system understood its actual content.

## Who This Affects
People who keep documents, receipts, IDs, and screenshots in Google Photos
(83% of surveyed active users named this as their hardest-to-find content type)
and need to retrieve a specific one — often under real time pressure (e.g.
needing a medicine photo while standing at a pharmacy).

## What the MVP Must Prove
That extracting and indexing the actual text content of a document-type image —
rather than relying on visual category or face tags — allows a user to
successfully retrieve the correct document among several similar-looking ones,
using a real search term (a name, amount, or document type mentioned in the text).

## Explicit Scope Decisions (and why)
- **Mini-library, not single-image demo:** The MVP must include multiple
  (5-10) uploaded documents, not just one. A single-image demo would trivially
  "succeed" without testing the actual failure mode (a document lost among many
  similar ones). This mirrors the real evidence: Samrat's medicine photo lost
  among many photos, payment screenshots lost among hundreds.
- **OCR-based text matching only — no query-suggestion UI, no structured field
  extraction.** These are real, validated ideas (see long-term/V2 notes) but are
  explicitly OUT of scope for this MVP, to keep the test clean: the 3-user test
  must isolate whether OCR-based matching itself works, not be confounded by a
  second feature.
- **Document-type images only — not a fix for vague/natural-language search
  on scenic photos.** That is a separate, related but distinct problem
  (negation handling, fuzzy memory) surfaced in interviews but deliberately
  not addressed here, to keep the MVP focused on one validated root cause.

## Success Criteria for the MVP
- A user can upload a small set of document-type images.
- A user can search using a real detail from the document's content (a name,
  amount, date, or document type) and the system returns the correct one,
  ranked above unrelated documents — because it matched the actual extracted
  text, not a face tag or visual category.
- This is testable by 3 real users attempting realistic retrieval tasks
  (e.g. "find the payment screenshot for amount X" among several screenshots).
