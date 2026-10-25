import pytest
from slothlab.ui.themes import DARK, LIGHT, THEMES, theme_css
from slothlab.ui.style import STYLE

@pytest.mark.parametrize('theme', THEMES)
def test_theme_has_readable_surface_and_widget_tokens(theme):
    css = theme_css(theme)
    assert css.startswith('<style>') and css.endswith('</style>')
    assert '--lab-ink:' in css and '--lab-field:' in css
    assert '[data-baseweb="input"]' in css
    assert 'http' not in css

def test_system_follows_browser_and_explicit_preferences_do_not():
    assert 'prefers-color-scheme: dark' in theme_css('System')
    assert 'prefers-color-scheme' not in theme_css('Dark')
    assert DARK['ink'] in theme_css('Dark')
    assert LIGHT['ink'] in theme_css('Light')
    assert STYLE == theme_css('Light')

def test_invalid_theme_is_not_silently_accepted():
    with pytest.raises(ValueError):
        theme_css('Neon')
