# Learning center and appearance

The help area includes a bundled 84-second silent animated lesson, six chapter jumps, English captions, complete readable/downloadable transcripts, practice questions with corrective feedback, and a research design checklist. The video teaches the actual application workflow and the registered prior-correction research protocol. It is an instructional animation, not a screen recording or a source of experimental results.

Chapters cover workspace navigation, testable hypotheses, controls and budgets, running and revising, held-out confirmation, and reporting uncertainty. Chapter navigation seeks the video to the corresponding timestamp. Playback continues through later chapters. The lesson never starts automatically. Standard browser playback controls provide pause, seeking, volume and caption settings; transcripts remain available when a browser cannot decode MP4. Interactive checks are learning aids and do not change experiment configuration or certify scientific validity.

System appearance follows the browser/device `prefers-color-scheme` preference. Light and Dark override it for the application. The CSS uses local fonts and assets, readable surface/text tokens, and native Streamlit controls. Charts drawn into a canvas need their own corresponding chart theme; CSS cannot recolor pixels already drawn into a canvas.

The static assets are `slothlab/data/tutorial/research-guide.mp4` (H.264, 960 × 540, no audio) and `research-guide.vtt`. They must be included in installed packages. Viewing requires no video-generation dependencies and no external service. To rebuild, install Pillow in a development environment and run `python -m slothlab.ui.build_tutorial /path/to/ffmpeg`; the generator uses the lesson definitions in `slothlab/ui/learning.py` and the system DejaVu Sans font. After changing lesson timing or text, rebuild the assets and run the learning tests.

The connections page explains that local and remote Ollama-compatible HTTP(S) endpoints are supported, while scientific experiments execute on the application host. Sending research context to a remote endpoint is different from running experiments remotely. Arbitrary OpenAI/Anthropic endpoints and authenticated gateways are not implemented by this adapter.

For a shareable product overview outside the application, see the [90-second illustrated overview](illustrated-demo.md).

An [actual automated browser recording](demo.md) demonstrates navigation, evidence review, portable export, guest restore, and local profiles.
