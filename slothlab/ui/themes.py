"""Appearance preferences without network calls or server-global settings."""
THEMES = ('System', 'Light', 'Dark')
LIGHT = {'bg':'#f5f7f8','panel':'#ffffff','ink':'#172a37','muted':'#526672','line':'#d5e0e4','accent':'#147b62','field':'#ffffff','soft':'#eaf2ef'}
DARK = {'bg':'#101b22','panel':'#182930','ink':'#edf5f4','muted':'#b4c8ce','line':'#38515a','accent':'#83dfba','field':'#20353e','soft':'#233e43'}

def _tokens(palette: dict[str, str]) -> str:
    return ';'.join(f'--lab-{key}:{value}' for key, value in palette.items()) + ';'

def theme_css(theme: str = 'System') -> str:
    """Return CSS with an explicit preference or browser color-scheme fallback."""
    if theme not in THEMES:
        raise ValueError(f'Unknown theme: {theme}')
    from slothlab.ui.style import BASE_CSS
    chosen = DARK if theme == 'Dark' else LIGHT
    tokens = f':root {{{_tokens(chosen)}color-scheme:{"dark" if theme == "Dark" else "light"};}}'
    if theme == 'System':
        tokens += f'@media (prefers-color-scheme: dark) {{:root {{{_tokens(DARK)}color-scheme:dark;}}}}'
    return '<style>' + tokens + BASE_CSS + '</style>'
