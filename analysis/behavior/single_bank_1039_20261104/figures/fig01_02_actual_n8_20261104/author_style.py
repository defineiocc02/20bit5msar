"""Current selected-paper typography; callers retain geometry, data and text roles."""
import matplotlib as mpl
from matplotlib import font_manager as fm

FONT = 'Arial'
ROLE_STYLES = {
    'plain': {'weight': 'normal', 'style': 'normal', 'size': 8},
    'plot': {'weight': 'normal', 'style': 'normal', 'size': 8},
    'panel': {'weight': 'normal', 'style': 'normal', 'size': 8},
    'variable': {'weight': 'bold', 'style': 'italic', 'size': 8},
    'callout': {'weight': 'bold', 'style': 'italic', 'size': 8},
    'index': {'weight': 'bold', 'style': 'normal', 'size': 6},
    'circuit_quantity': {'weight': 'bold', 'style': 'normal', 'size': 8},
    'circuit_block': {'weight': 'bold', 'style': 'normal', 'size': 8},
    'source_bold_heading': {'weight': 'bold', 'style': 'normal', 'size': 8},
    'scientific_exponent': {'weight': 'normal', 'style': 'normal', 'size': 6},
}


def role(name='plain', **overrides):
    """Return Text keyword arguments; exact 6pt indices need explicit placement."""
    result = {'family': FONT, **ROLE_STYLES[name]}
    result.update(overrides)
    return result


def apply(source_specific=None):
    """Set Regular8 plot defaults; explicit rcParams overrides are permitted."""
    for style, weight, expected_face in [
        ('normal', 'normal', 'ArialMT'),
        ('normal', 'bold', 'Arial-BoldMT'),
        ('italic', 'bold', 'Arial-BoldItalicMT'),
    ]:
        path = fm.findfont(fm.FontProperties(family=FONT, style=style, weight=weight),
                           fallback_to_default=False)
        name = fm.FontProperties(fname=path).get_name()
        actual_face = fm.get_font(path).postscript_name
        if name != FONT or actual_face != expected_face:
            raise RuntimeError('Expected ' + expected_face + ', found '
                               + str(actual_face) + ' at ' + path)
    defaults = {
        'font.family': FONT, 'font.weight': 'normal', 'font.style': 'normal',
        'font.size': 8, 'axes.labelweight': 'normal', 'axes.labelsize': 8,
        'axes.titlesize': 8, 'axes.titleweight': 'normal',
        'xtick.labelsize': 8, 'ytick.labelsize': 8, 'legend.fontsize': 8,
        'axes.linewidth': 0.7, 'xtick.major.width': 0.7, 'ytick.major.width': 0.7,
        'grid.linewidth': 0.45, 'lines.linewidth': 1.0,
        'lines.markersize': 3.0, 'lines.markeredgewidth': 0.65,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'text.color': 'black',
        'axes.edgecolor': 'black', 'axes.labelcolor': 'black',
        'xtick.color': 'black', 'ytick.color': 'black',
        'lines.solid_capstyle': 'butt', 'lines.solid_joinstyle': 'miter',
        'lines.dash_capstyle': 'butt', 'lines.dash_joinstyle': 'miter',
        'path.simplify': False,
        'pdf.fonttype': 42, 'ps.fonttype': 42, 'svg.fonttype': 'none',
        'mathtext.fontset': 'custom', 'mathtext.rm': 'Arial',
        'mathtext.it': 'Arial:style=italic:weight=bold',
        'mathtext.bf': 'Arial:weight=bold', 'mathtext.sf': 'Arial',
    }
    if source_specific is not None:
        defaults.update(source_specific)
    mpl.rcParams.update(defaults)


def finish(fig, source_specific=None):
    """Keep explicit roles; normalize axis/legend family without forcing Bold/Italic.

    Optional source_specific maps axis_labels, ticks or legend to Text properties.
    Existing apply()/finish(fig) callers remain valid.
    """
    overrides = {} if source_specific is None else source_specific
    for ax in fig.axes:
        groups = {
            'axis_labels': [ax.xaxis.label, ax.yaxis.label, ax.title],
            'ticks': ax.get_xticklabels() + ax.get_yticklabels()
                     + [ax.xaxis.get_offset_text(), ax.yaxis.get_offset_text()],
            'legend': [] if ax.get_legend() is None else ax.get_legend().get_texts(),
        }
        for group, labels in groups.items():
            for label in labels:
                label.set_fontfamily(FONT)
                label.set(**overrides.get(group, {}))
