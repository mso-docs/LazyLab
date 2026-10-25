"""Offline, chapter-based learning center with an accessible video companion."""
from dataclasses import dataclass
from pathlib import Path
import streamlit as st

ASSETS = Path(__file__).resolve().parents[1] / 'data' / 'tutorial'
VIDEO = ASSETS / 'research-guide.mp4'
CAPTIONS = ASSETS / 'research-guide.vtt'

@dataclass(frozen=True)
class Chapter:
    title: str
    start: int
    duration: int
    action: str
    transcript: str
    question: str
    choices: tuple[str, ...]
    answer: int
    explanation: str

CHAPTERS = (
 Chapter('Orient your workspace',0,14,'Open Research to review investigations. Use New investigation to start a question.',
 'The Research workspace holds investigations, hypotheses, experiments and reports. Choose an existing investigation to inspect its evidence. Open New investigation to begin. Sample lesson diagrams are illustrations, not experimental results.',
 'Where should you begin a fresh research question?',('New investigation','Delete an existing result','Comparisons only'),0,'New investigation creates a separate research record with its own objective and budget.'),
 Chapter('Ask a testable question',14,14,'Write an objective, a falsifiable hypothesis and a competing explanation.',
 'Use a question the registered experiment can actually test: does prior correction improve Brier score under a specified label shift? State a prediction and a competing prediction. The current scientific domain is prior correction, not arbitrary laboratory research.',
 'Which hypothesis can this experiment test?',('Correction always makes every model perfect','Under a specified label shift, correction reduces Brier score','AI will transform science'),1,'Specify a measurable outcome and conditions. A competing prediction makes contrary evidence meaningful.'),
 Chapter('Set controls and a budget',28,14,'Choose conditions deliberately. Reserve independent seeds before running.',
 'Hold data geometry and unrelated parameters fixed when comparing conditions. Separate exploration seeds from reserved confirmation seeds. Declare a finite experiment and token budget. Exact configuration and seed reuse is caching; a new seed is an independent replication.',
 'What makes a useful replication?',('Reusing the exact same configuration and seed','Changing every parameter together','Keeping the condition fixed with a new independent seed'),2,'A new independent seed tests variability; an exact repeat can be served from memory.'),
 Chapter('Run, inspect and revise',42,14,'Start the investigation. Follow events and evidence; pause or resume when needed.',
 'The loop proposes hypotheses, runs registered experiments and evaluates evidence. Watch the event log and experiment records. Revisions produce a new untested hypothesis; do not treat a rewritten claim as already confirmed. A stop caused by a budget limit is a legitimate outcome.',
 'A revised hypothesis is…',('A new untested claim','Automatically confirmed','A reason to erase contrary results'),0,'Revision changes the claim, so it needs its own evidence and provenance.'),
 Chapter('Confirm without tuning',56,14,'Freeze the selected condition, then evaluate its reserved confirmation batch.',
 'Use reserved seeds only after exploration. Final confirmation needs at least three independent seeds per condition. Do not optimize again against confirmation outcomes. Mixed evidence can remain insufficient; COMPLETED means declared operational criteria passed, not a universal scientific law.',
 'After inspecting confirmation results, should you tune against them?',('Yes, until every run improves','No; preserve confirmation as a held-out check','Only by dropping inconvenient seeds'),1,'Tuning on the held-out batch turns it into exploration and weakens the confirmation claim.'),
 Chapter('Interpret and share evidence',70,14,'Read uncertainty and provenance, then export the investigation and reports.',
 'Delta Brier equals corrected minus baseline Brier score. Negative values favor correction; positive values favor the baseline. Report variability and uncertainty alongside the average. An interval spanning zero does not establish a clear improvement. Export reports and preserve configuration, seeds, hypothesis IDs and model provenance.',
 'What does a negative delta Brier mean?',('Correction had lower Brier score in that comparison','Every future experiment will improve','The baseline was more accurate'),0,'Lower Brier is better. A measured improvement still needs context, replication and uncertainty.'),
)

def answer_feedback(chapter: int, selected: int) -> tuple[bool, str]:
    lesson = CHAPTERS[chapter]
    if not 0 <= selected < len(lesson.choices):
        raise ValueError('Answer index is out of range')
    return selected == lesson.answer, lesson.explanation

def render_learning_center() -> None:
    st.subheader('Learn the research workflow')
    st.caption('An 84-second animated guide with chapter navigation, captions and practice questions. Silent visual lesson; not a recording of a live investigation.')
    walkthrough, design, connection = st.tabs(['Guided walkthrough', 'Research design checklist', 'Connections & troubleshooting'])
    with walkthrough:
        index = st.selectbox('Jump to a chapter', range(len(CHAPTERS)), format_func=lambda i: f'{i+1}. {CHAPTERS[i].title}', key='learning_chapter')
        chapter = CHAPTERS[index]
        st.progress((index + 1) / len(CHAPTERS), text=f'Chapter {index+1} of {len(CHAPTERS)} · {chapter.start // 60}:{chapter.start % 60:02d}')
        if VIDEO.is_file():
            st.video(str(VIDEO), start_time=chapter.start, subtitles={'English': str(CAPTIONS)} if CAPTIONS.is_file() else None)
        else:
            st.info('The tutorial video is unavailable in this installation. The complete lesson and exercises remain available below.')
        st.markdown(f'### {chapter.title}')
        st.write(chapter.action)
        with st.expander('Read this chapter’s transcript', expanded=True):
            st.write(chapter.transcript)
        selected = st.radio(chapter.question, range(len(chapter.choices)), format_func=lambda i: chapter.choices[i], index=None, key=f'learning_answer_{index}')
        if st.button('Check my understanding', key=f'learning_check_{index}'):
            if selected is None:
                st.info('Choose an answer first.')
            else:
                correct, explanation = answer_feedback(index, selected)
                (st.success if correct else st.warning)(('Correct. ' if correct else 'Try again. ') + explanation)
        previous, following = st.columns(2)
        def move(offset: int) -> None:
            st.session_state.learning_chapter += offset
        previous.button('← Previous chapter', disabled=index == 0, on_click=move, args=(-1,), key='learning_previous')
        following.button('Next chapter →', disabled=index == len(CHAPTERS)-1, on_click=move, args=(1,), key='learning_next')
        transcript = '\n\n'.join(f'{i+1}. {c.title}\n{c.transcript}' for i,c in enumerate(CHAPTERS))
        st.download_button('Download complete transcript', transcript, 'slothlab-research-guide.txt', mime='text/plain', key='learning_transcript')
    with design:
        st.markdown('### Before you run')
        items = (
          'My question fits the registered prior-correction experiment.',
          'My hypothesis predicts a measurable outcome and names conditions.',
          'I have a competing prediction that could explain contrary evidence.',
          'I can identify what changes and which parameters remain fixed.',
          'I reserved independent confirmation seeds before exploration.',
          'My finite experiment and token budgets fit the question.',
          'My stopping criteria and interpretation of uncertainty are explicit.',
        )
        checked = [st.checkbox(label, key=f'learning_design_{i}') for i,label in enumerate(items)]
        st.progress(sum(checked)/len(items), text=f'{sum(checked)} of {len(items)} design checks considered')
        st.caption('This checklist is a planning aid. Checking boxes does not validate a protocol or change the investigation configuration.')
        st.markdown('### A concrete hypothesis')
        st.write('For a fixed class-conditional geometry and a specified change in prevalence, prior correction will reduce mean Brier score across independent seeds. Competing prediction: estimation or calibration error offsets that benefit.')
        st.info('Write the actual conditions and criteria in your investigation. Use uncertainty and negative results to refine the claim, rather than selecting only favorable runs.')
    with connection:
        st.markdown('### Local or remote AI inference')
        st.write('Both are supported through an Ollama-compatible HTTP(S) endpoint. A local URL runs inference on that machine; a remote URL sends prompts and research context to that server. The registered scientific experiments still execute on the application host.')
        st.write('Set the model endpoint in the application or OLLAMA_BASE_URL before launch. Use the base server address, not /api/chat. Select a model already installed on that server. This integration does not implement arbitrary OpenAI or Anthropic APIs, or an authenticated gateway.')
        st.markdown('### If a run cannot start')
        st.write('Check the endpoint, installed model name and server reachability. A remote service must be reachable from the app host. Review the visible error and event log, then correct the configuration. Never place passwords or API keys inside the URL.')
        st.markdown('### Read the outcome accurately')
        st.write('A budget stop, insufficient evidence or a failed experiment is not a confirmed hypothesis. Review execution status separately from measured scientific evidence. Keep exports with the settings and seeds needed to reproduce them.')
