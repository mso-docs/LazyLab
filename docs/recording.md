# Automated live recording

The [docs demo](demo.md) includes a recording of the actual Streamlit application, captured in a fresh Playwright Chromium context. No person needs to operate the browser. The automation switches themes, reviews the design form, inspects a previously completed investigation, downloads a real portable bundle, reopens it in Guest mode, visits learning tools, and creates a separate demo browser profile.

The displayed investigation predates the recording. This demonstrates navigation and actual export/import, not a new autonomous research run. Recorded measurements remain scoped to their original experiment and finite protocol.

## Reproduce

Use an isolated copy of a workspace containing a completed investigation with valid artifacts. Keep paths relative to the repository, use a demonstration profile name, and keep unrelated private history out of that copy. Start the dashboard on a separate loopback port; do not point the automation at a personal workspace.

```bash
SLOTHLAB_ARTIFACT_DIR=artifacts \
SLOTHLAB_JOB_DIR=artifacts/public-demo/jobs \
SLOTHLAB_PROFILE_DIR=artifacts/public-demo/profiles \
slothlab --db artifacts/public-demo/research.sqlite dashboard --port 8502
```

In another terminal, install the optional recording tools outside the application environment:

```bash
npm install --prefix /tmp/slothlab-demo-tools playwright
/tmp/slothlab-demo-tools/node_modules/.bin/playwright install chromium
```

Run the recording from the repository root. Set `DEMO_SESSION` to the exact research-session option shown in your demo workspace. The default selects the original verified investigation used for the published video.

```bash
NODE_PATH=/tmp/slothlab-demo-tools/node_modules \
DEMO_URL=http://127.0.0.1:8502 \
node scripts/record_live_demo.cjs

python scripts/finalize_live_demo.py /path/to/ffmpeg
```

Finalization additionally requires Pillow. It encodes H.264 MP4, removes initial browser setup, decodes the full result to check for errors, and produces captions, a transcript, and a poster. Raw videos, screenshots, downloaded research bundles and chapter timings stay under ignored `artifacts/public-demo/recording/`. Public deliverables go to `docs/media/slothlab-live-demo*`. A contact sheet is written to `/tmp/slothlab-live-demo-contact.png` for review.

The recorder checks each chapter for visible personal home paths and email addresses. That check is limited: review the complete recording before publication for other private research, credentials, or unrelated content. It captures only the isolated browser viewport, with no personal browser profile, desktop, audio, or notifications. Model discovery contacts the configured Ollama server; the script does not launch inference. Import and profile creation write only to the isolated demo and temporary guest workspaces.

The scripts intentionally stop on failed selectors or operations. Failed recordings remain ignored and are not finalized as public documentation. Changes to the application may require updating UI selectors in the recording script.
