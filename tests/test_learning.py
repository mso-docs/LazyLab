from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest
from slothlab.ui.learning import CHAPTERS, VIDEO, CAPTIONS, answer_feedback


def test_chapter_timing_and_bundled_video():
    assert CHAPTERS[0].start == 0
    for first, second in zip(CHAPTERS, CHAPTERS[1:]):
        assert first.start + first.duration == second.start
    assert CHAPTERS[-1].start + CHAPTERS[-1].duration == 84
    data = VIDEO.read_bytes()
    assert data[4:8] == b'ftyp' and len(data) > 10000
    captions = CAPTIONS.read_text()
    assert captions.startswith('WEBVTT')
    assert captions.count(' --> ') == len(CHAPTERS)
    assert '00:01:24.000' in captions

@pytest.mark.parametrize('index', range(len(CHAPTERS)))
def test_quiz_distinguishes_correct_and_incorrect_answers(index):
    chapter = CHAPTERS[index]
    for selected in range(len(chapter.choices)):
        correct, explanation = answer_feedback(index, selected)
        assert correct == (selected == chapter.answer)
        assert explanation
    with pytest.raises(ValueError):
        answer_feedback(index, 99)


def test_learning_center_navigation_and_feedback():
    app = AppTest.from_string('from slothlab.ui.learning import render_learning_center\nrender_learning_center()').run()
    assert not app.exception
    app.button(key='learning_check_0').click().run()
    assert any('Choose an answer' in value.value for value in app.info)
    app.radio(key='learning_answer_0').set_value(0).run()
    app.button(key='learning_check_0').click().run()
    assert any('Correct.' in value.value for value in app.success)
    app.button(key='learning_next').click().run()
    assert app.selectbox(key='learning_chapter').value == 1
    app.selectbox(key='learning_chapter').set_value(5).run()
    assert app.button(key='learning_next').disabled
    assert not app.exception
