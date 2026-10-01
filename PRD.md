# PRD — MVP: OCR-Based Document Search
## For Google Photos Retrieval Research Project

## 1. Overview
Build a small, functional web app that demonstrates OCR-based document search —
the validated fix for the confirmed root cause (Google Photos doesn't read text
inside document-type images). This is a standalone prototype, not an integration
with real Google Photos.

**One feature only.** No query-suggestion UI, no structured field extraction —
those are V2/long-term ideas, explicitly out of scope here (see Problem
Statement, Explicit Scope Decisions).

## 2. Core User Flow
1. User uploads several document-type images (5-10) — e.g. ID cards, payment
   screenshots, receipts, medicine labels, mark sheets. Can be real (anonymized/
   dummy data recommended) or realistic mock examples.
2. On upload, the system runs OCR on each image and extracts/stores the text
   content alongside the image.
3. User types a search query into a search bar (e.g. "payment 6500," "Samrat
   Aadhaar," "invoice March").
4. System matches the query against the extracted OCR text (not image embeddings,
   not face tags, not filename) and returns ranked results — the image(s) whose
   extracted text best matches the query, shown first.
5. User can click a result to view the full image.

## 3. Technical Requirements

**OCR:** Use a reliable, free/open-source OCR library — Tesseract (pytesseract)
is the standard choice and sufficient for this MVP. No need for a paid/cloud OCR
API unless Tesseract's accuracy proves too poor on test images.

**Matching logic:** Simple, explainable text matching is sufficient for the MVP —
does not need to be a full semantic search system. A reasonable approach:
- Extract OCR text per image, store as plain text alongside the image reference
- On search, do a straightforward relevance match (e.g. keyword overlap, or a
  simple TF-IDF/fuzzy string match) between the query and each image's extracted
  text
- Rank and return results by match score, highest first
- If no extracted text matches at all, return "no results" rather than falling
  back to showing unrelated images (this is important — it must behave
  differently from Google Photos' current behavior, which shows an irrelevant
  pile rather than admitting no match)

**Frontend:** Simple, single-page web app:
- Upload area (multiple file upload)
- Search bar
- Results area showing matched image(s) with a visible snippet of the matching
  extracted text (so the user can see *why* this result was returned — this is
  important for demonstrating the mechanism clearly to evaluators)
- "No results found" state for queries with no match

**Backend:** Python (Flask, consistent with the discovery-engine demo app) —
handles file upload, OCR processing, and search matching.

**Deployment:** Deploy on Render (same as the discovery-engine demo), free tier,
with a public shareable link.

## 4. Test Data Requirements
Prepare 5-10 realistic but safe-to-share mock documents before testing with real
users — for example:
- A mock payment screenshot showing an amount and a name
- A mock ID-card-style image with a name
- A mock receipt/invoice
- A mock medicine label
- A mock mark sheet/certificate
- 2-3 "distractor" documents of similar visual type but different content, to
  genuinely test whether the system can discriminate between similar-looking
  documents (this is the core claim being tested — see Problem Statement)

Do NOT use real personal documents (real Aadhaar numbers, real bank details,
etc.) for anything that will be shared publicly or used in user testing —
use clearly mock/dummy data that resembles the real format.

## 5. What This MVP Must Demonstrate (for the 3-user test)
Give each test user a realistic retrieval task, e.g.: "Find the payment
screenshot where the amount was ₹6500" or "Find the ID card belonging to
[name]" — among the 5-10 uploaded documents. Success = the user finds the
correct document using a natural search term, faster and more reliably than
they described in their interview experience with the real Google Photos app.

## 6. Non-Goals (explicit)
- No query-suggestion UI (V2)
- No structured field extraction / categorization (V2)
- No fix for vague/natural-language search on non-document (scenic) photos —
  out of scope, different root cause
- No real integration with Google Photos — this is a standalone demonstration
  of the mechanism, not a shipped feature
- No user accounts/login — single-session use is sufficient for this MVP

## 7. Deliverable
- A working, publicly deployed web app (Render link)
- Pre-loaded or easily-uploadable mock document set for testing
- Clear visible "why this matched" text snippet in results, so the mechanism
  is transparent to anyone testing or evaluating it
