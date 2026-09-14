 # Automated Invoice-to-Booking System — Development Plan

## Objectives & Success Metrics
- **Primary goal**: Ship a local, end-to-end MVP for automated invoice-to-booking (steps 8c–10) with GREEN/YELLOW/RED governance.
- **Compliance**: Deterministic validations R0–R8; auditability aligned to GoBD; GDPR-compliant pseudonymization.
- **Quality metrics**:
  - 100% unit test pass for R3/R4 tolerance checks and R0 precedence.
  - E2E processing of 4 synthetic PDFs with expected GREEN/YELLOW/RED outcomes.
  - Deterministic double-entry equality with 0.00 EUR delta.
  - Frontend revalidation loop < 1s after clerk update on YELLOW.

## Scope (MVP) and Non-Goals
- **In scope**: PDF ingestion with OCR fallback; PII pseudonymization; hybrid extraction + deterministic rules; R0–R8 engine; account suggestion; booking proposal; REST API; React UI; MongoDB persistence; basic audit trail.
- **Deferred to production track**: EN 16931 XML ingestion; creditor subledger + IBAN verification; WORM immutability; RBAC/four-eyes; multi-line/tax splitting; external VAT registry checks (BZSt/VIES).

## Architecture Overview
- **Frontend**: React (Vite) SPA with PDF viewer, status badge, editable extracted fields, validation panel, booking table.
- **Backend**: FastAPI (Python) async service: PDF ingestion, extraction pipeline, pseudonymization module, deterministic rules engine, booking proposal builder, REST endpoints.
- **Database**: MongoDB for invoices, master data (clients, creditors, accounts), and audit_events (append-only).
- **Neuro-symbolic hybrid**: OCR/vision + semantic extraction, governed by deterministic rule checks R0–R8.
- **Privacy**: In-memory reversible pseudonymization for PII; optional external model calls under DPA, zero-retention.

## Detailed Pipeline (Steps 8c–10)
- **8c Ingestion & Extraction**: Receive PDF → parse via pdfplumber/PyMuPDF → OCR fallback (pytesseract) → locale-safe number parsing → Decimal.
- **8d Validation**: Deterministic checks R1–R6 and R8; mathematical tolerances at 0.02 EUR; precedence via R0 to compute traffic light and blocked state.
- **9 Account Assignment**: Known creditor → default expense account; otherwise semantic keyword mapping; low confidence ⇒ R7 YELLOW.
- **10 Booking Proposal**: DEBIT 42xx/49xx and 1571/1576 based on VAT rate; CREDIT 1600; exact balance identity.

## REST Endpoints
- POST `/api/invoices/upload`
- GET `/api/invoices`
- GET `/api/invoices/{id}`
- GET `/api/invoices/{id}/pdf`
- POST `/api/invoices/{id}/revalidate`
- GET `/api/master-data`

## MongoDB Collections
- `invoices`, `clients`, `creditors`, `accounts`, `audit_events` (append-only).

## Business Rules (R0–R8)
- **R0 Status-Priorität**: RED ≻ YELLOW ≻ GREEN for overall status.
- **R1 Rechnungsempfänger (RED)**: Must match client master (name + VAT ID).
- **R2 Pflichtfelder (RED)**: Invoice number, invoice date, net, vat, gross, currency.
- **R3 Betragsprüfung (RED)**: |Net + VAT − Gross| ≤ 0.02 EUR.
- **R4 USt.-Plausibilität (RED)**: |Net × (Rate/100) − VAT| ≤ 0.02 EUR.
- **R5 Leistungsdatum (YELLOW)**: Presence of service date/interval.
- **R6 Kreditorenstamm (YELLOW)**: Vendor in creditor master via VAT/IBAN/name.
- **R7 Kontierung (YELLOW)**: Unambiguous expense account mapping.
- **R8 Happy Path (GREEN)**: No RED, no YELLOW, unambiguous account.

## Security & Privacy Controls
- Local parsing and NER-based PII detection (VAT IDs, IBANs, names, addresses, emails, phones).
- Surrogate substitution `<ENTITY_TYPE_INDEX>`; mappings stored only in volatile memory; never persisted or transmitted.
- Optional external model calls under enterprise DPA, zero data retention.

## Testing Strategy
- **Unit**: R3/R4 math tolerances; R0 precedence; account suggester; booking balance.
- **Integration**: Upload→extract→validate→persist; revalidate loop; PDF streaming.
- **E2E**: 4 synthetic PDFs across GREEN/YELLOW/RED via UI.
- **Security**: No PII in logs or outbound payloads.

## Risks & Mitigations
- OCR quality on scans → pre-processing; YELLOW fallback.
- PII leakage → local-only mode; redaction tests.
- Rounding errors → Decimal everywhere; locale parsing; tolerance tests.
- Misclassification → low-confidence threshold; curated keywords; human-in-the-loop feedback.

## Implementation Milestones and Timeline (8 Weeks)
- **Phase 1: Backend & DB Foundation (W1–2)**
  - FastAPI scaffolding; Mongo connection; endpoints upload/list/get/pdf.
  - PDF parsing with OCR fallback; seed data script; sample PDFs.
- **Phase 2: Security & Rule Engine (W3–4)**
  - Pseudonymization (regex+checksum+NER) with in-memory vault.
  - Deterministic rules R1–R6, R8; R0 precedence; Decimal-based tolerances.
- **Phase 3: Ledger Logic & Endpoints (W5)**
  - Account suggester; proposal builder; `/revalidate` endpoint.
- **Phase 4: React Frontend & Integration (W6–7)**
  - Vite SPA; PDF viewer; status+forms+audit+booking; API integration; E2E.
- **Release & Docs (W8)**
  - UAT; “Verfahrensdokumentation” draft; ops runbook; ADRs.

## Acceptance Criteria by Phase
- **Phase 1**
  - Upload returns record ID; GET PDF streams; text extracted or OCR fallback operational.
- **Phase 2**
  - R3/R4 tolerances enforced; R0 precedence correct; pseudonymization verified via tests; audit entries persisted.
- **Phase 3**
  - Known creditor → default account; keywords map categories; low confidence ⇒ R7; balanced booking lines.
- **Phase 4**
  - GREEN exposes booking export; YELLOW editable → revalidation <1s; RED blocks with clear reasons; 4 PDFs match expected payloads.

## Report Deliverable Plan
- Executive summary; legal basis (GoBD, AO/HGB, §14 UStG, e-invoicing timeline).
- Architecture; security & pseudonymization; 8c–10 pipeline with rules; data model & endpoints; sample GREEN/RED payloads; tests; ops & auditability; production roadmap.
- Draft end Week 7; final Week 8; reviews by Accounting SME, Privacy Officer, Security.

## Immediate Next Steps (Week 1)
- Initialize repo structure (backend/, frontend/, docs/).
- Implement FastAPI app with health check and stubbed invoice endpoints.
- Add requirements.txt and basic tests.
- Plan seed data layout for clients, creditors, accounts.
