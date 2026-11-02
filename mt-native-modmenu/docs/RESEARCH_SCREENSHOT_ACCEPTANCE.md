# Research-only screenshot and global policy evidence acceptance

- Screenshot: explicit user request and consent required; capture uses TextureView.getBitmap for an already-authorized view, not an unverified MetaTrader host. No implicit upload, remote transmission or persistent image storage.
- Host must supply a validated TextureView reference. ModeMenu screenshot button remains disabled without a callback.
- Captured image must be reviewed by the user before any external sharing; no OCR/LLM image interpretation is implemented.
- Source collector: ResearchEvidenceGate validates pre-fetched records. It does not fetch web pages itself, and is not an autonomous web agent.
- Official domains include Fed, ECB, BoE, BoJ, RBA, RBNZ, BoC, SNB, BNM and BIS. Reject non-HTTPS, lookalike hosts, future/stale evidence and duplicates.
- Classification: FundamentalResearch uses a limited keyword dictionary. Negation, quotation context and comparative monetary-policy interpretation are not implemented; never represent it as a validated AI signal.
- No live broker orders, no screenshots uploaded, no provider API keys, no deployment and no billing changes.
- Android SDK compilation and device behavior remain separate release gates.
