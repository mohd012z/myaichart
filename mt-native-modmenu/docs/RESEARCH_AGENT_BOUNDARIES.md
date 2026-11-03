# Fundamental research module — evidence and release gates

## Existing functionality
- User-triggered HTTP GET to explicitly allowlisted official central-bank hostnames; redirects, large bodies, binary content, and non-200 responses rejected.
- Network source fetcher returns raw text or HTML. It does not extract article text, verify published date, cite statements, summarize articles, or run unattended.
- ResearchEvidenceGate accepts externally supplied metadata; the fetcher currently sets the fetch time as a placeholder publication time. **Do not treat that as the actual publication date**. A verified document publication timestamp must be extracted before time-sensitive policy classification.
- FundamentalResearch performs phrase matching only; cannot understand negation, context or relative rate paths.
- ScreenshotPreview is ephemeral and has no automatic upload. ChartScreenshotCapture requires a verified TextureView and user consent.
- Screenshot button still needs an authorized host callback and a preview flow. It remains disabled without that callback.

## Release blockers
- No Android SDK compilation evidence or signed installable APK.
- No verified MT5 chart hierarchy integration or instrumentation tests.
- No verified live official-site retrieval, publication timestamp parser, economic-calendar feed or source-citation UI.
- No image understanding model connected. No background web agent.
- No broker orders or trading automation.
