---
title: "I built a local research agent that knows when to stop"
published: false
tags: ai, python, opensource, showdev
---

An AI research loop can generate another experiment long after it has stopped learning anything useful. I wanted a small laboratory where I could inspect what the agent ran, why it ran it, and why it stopped.

That became **SlothLab + LazyLoop**: a local scientific research application with a Streamlit workspace, an Ollama-compatible model connection, reproducible experiments, and a controller that treats compute as a finite resource.

[Source code](https://github.com/mso-docs/LazyLab) · [Static evidence explorer](https://mso-docs.github.io/LazyLab/) · [Video help guide](https://mso-docs.github.io/LazyLab/help.html)

{% youtube UV3h4IRk3go %}

The video is an actual automated browser recording. It explores a previously completed investigation, downloads its research bundle, and reopens that history in Guest mode. It does not show a new autonomous investigation finishing in 96 seconds.

## Start with a narrow scientific question

The first experiment family studies **oracle prior-probability correction under synthetic class prevalence shift**.

In practical terms: if the class balance changes, when does adjusting predicted probabilities improve Brier score? The experiment supplies the true evaluation prevalence as an oracle input. That assumption is part of the research question, not a capability to infer prevalence from arbitrary real-world data.

This scope gives the agent something measurable to do. It proposes hypotheses and registered experiment specifications; deterministic Python procedures execute the science. It cannot invent a shell command and call that an experiment.

The workflow is:

```text
Question → hypotheses → validated candidates
                    ↓
           execute / reuse / reject
                    ↓
         measurements → interpretation
                    ↓
         independent confirmation or stop
```

A model explanation remains provisional. It does not become a scientific finding simply because it sounds confident.

## Let code enforce the research boundary

LazyLoop validates proposed conditions, checks budget feasibility, finds verified exact-result matches, and tracks whether the investigation is progressing.

For example, this is real validation code from `slothlab/lazyloop/controller.py`:

```python
allowed_seeds = (
    config.exploratory_seeds
    if spec.phase == "exploratory"
    else config.confirmatory_seeds
)
if spec.seed not in allowed_seeds:
    raise ValueError("Seed does not belong to its predeclared phase partition")
```

That check expresses a research decision: confirmation seeds are reserved before exploration. The agent cannot quietly recycle exploration into independent confirmation by changing the label.

Exact-result reuse is another useful distinction. Repeating an identical experiment can return a verified cached result. Changing the seed can create a genuinely independent replication. A cache hit must never count as a second independent measurement.

## What the completed example actually showed

One recorded investigation reached its declared operational completion criteria with:

- Five original experiment executions.
- One verified exact-result reuse.
- Three independent confirmation seeds for a fixed condition.
- 10,712 model tokens.

The mean confirmatory delta Brier was approximately **−0.00619**, where delta means corrected minus baseline. The three confirmation measurements supported improvement for that particular synthetic condition.

That is a scoped result. It does not show that correction helps every dataset or that this agent generally saves compute. Fixed-schedule replay comparisons exercised reuse, but the repeated autonomous evaluation did **not** establish an efficiency advantage with sufficient confirmatory coverage. Those are different claims, so the reports keep them separate.

[The original example and measured reports](https://github.com/mso-docs/LazyLab/tree/main/docs/examples/complete-investigation) are available for inspection.

## Make the application usable between experiments

The Streamlit interface handles investigation design, measurements, decisions, pause/resume, reports, and comparisons. Background research runs in a separate local process, so closing a browser tab does not itself abandon a job.

I also added the features that make repeated use less awkward:

- Light, Dark, and System appearance.
- Remembered local browser profiles with separate histories.
- Guest research using JSON documents and artifact files, without SQL.
- Portable ZIP bundles that can be downloaded and reopened.
- A learning area with chapter navigation, captions, transcripts, practice questions, and a research-design checklist.

A browser profile is a convenience on a trusted local installation, not a cross-device identity service. Guest mode uses temporary files; it is not a promise of secure erasure. Imported archives are validated data, and opening one starts no inference.

Inference can run locally or on a reachable remote **Ollama-compatible HTTP(S) server**. Scientific experiments and research files stay on the app host. The adapter does not support arbitrary OpenAI/Anthropic APIs or authenticated gateways.

## A static demo should tell the truth

GitHub Pages cannot run the Python research application. The static demo instead lets visitors filter real recorded measurements, inspect an experiment table, read the limitations, and download research-design notes.

Those notes are a planning worksheet, not executable configuration. The page makes no model calls. The help page embeds the YouTube walkthrough after an explicit playback action and explains how to run the full app.

This makes the project explorable without pretending a static website is carrying out scientific work.

## Verification and remaining work

The 0.2.0 acceptance run passed **214 tests**, including live Ollama checks, job pause/resume, portable-history validation, and JSON-only research workflows. The later live browser walkthrough additionally exercised real bundle download, guest restore, and local-profile creation.

The application is intended for a single-user Linux installation bound to loopback. It is not a reviewed public multi-tenant service. Execution isolation depends on the host; a restricted subprocess fallback is weaker than working OS namespaces. Passing tests does not remove those deployment limits.

The next useful work is broader scientific families and stronger evaluation across independent autonomous trials. I would rather preserve an insufficient-evidence outcome than turn a demo into an efficiency claim the measurements do not support.

## Try it locally

With Python 3.12+, Ollama running separately, and an installed model:

```bash
git clone https://github.com/mso-docs/LazyLab.git
cd LazyLab
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dashboard]'
export OLLAMA_MODEL='your-installed-model'
slothlab init
slothlab doctor
slothlab dashboard
```

Open `http://127.0.0.1:8501`. Start with a small, explicit question and a finite budget.

I would especially value feedback on where the evidence trail is unclear, which stopping decisions deserve stronger tests, and which first-run steps need better explanation.

### Related DEV discussions

[A Local-First Coding Agent Needs a Measurable Boundary](https://dev.to/_firelinks/a-local-first-coding-agent-needs-a-measurable-boundary-2cen), by [@_firelinks](https://dev.to/_firelinks), argues for making an agent's limits inspectable. That is a useful lens for assessing SlothLab's registered procedures and explicit budgets.

[How Do We Evaluate AI Agents? A Practical, End-to-End Framework for Reliability and Scale](https://dev.to/kuldeep_paul/how-do-we-evaluate-ai-agents-a-practical-end-to-end-framework-for-reliability-and-scale-4ed), by [@kuldeep_paul](https://dev.to/kuldeep_paul), discusses evaluating trajectories and efficiency alongside outcomes. SlothLab's distinction between fixed replay, autonomous runs, and scientific confirmation follows that broader evaluation concern; it does not depend on the commercial tools discussed in that article.

*Disclosure: AI assisted the implementation and preparation of this draft. The reported measurements come from recorded executions; the limitations above are part of the result.*
