#!/usr/bin/env python3
"""
make_slides.py  —  generates how_to.pdf with a 1980s Microsoft aesthetic.
Run: python make_slides.py
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib.backends.backend_pdf import PdfPages
from pathlib import Path

OUT = Path(__file__).parent / "how_to.pdf"

# ── Palette ────────────────────────────────────────────────────────────────
BG     = '#000080'
TBAR   = '#0000B8'
FG     = '#FFFFFF'
YELLOW = '#FFFF00'
CYAN   = '#00FFFF'
SILVER = '#9999CC'

W, H   = 13.33, 7.5
MGAP   = 0.38
CX     = 0.80
TBAR_H = 0.80

LEAD = 0.0198   # data-unit line advance per pt (~1.43x leading)


# ── Helpers ────────────────────────────────────────────────────────────────

def new_slide():
    fig = plt.figure(figsize=(W, H))
    fig.patch.set_facecolor(BG)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor(BG)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis('off')
    for lw, d in [(3.2, 0.0), (0.9, 0.14)]:
        m = MGAP + d
        ax.add_patch(mp.Rectangle((m, m), W - 2*m, H - 2*m,
                                   lw=lw, ec=FG, fc='none'))
    return fig, ax


def header(ax, title, subtitle=None):
    by = H - MGAP - TBAR_H
    ax.add_patch(mp.Rectangle((MGAP + 0.15, by), W - 2*(MGAP + 0.15),
                               TBAR_H, lw=0, fc=TBAR))
    ax.plot([MGAP + 0.15, W - MGAP - 0.15], [by, by], color=FG, lw=1.5)
    ty = by + TBAR_H * (0.67 if subtitle else 0.5)
    ax.text(W / 2, ty, title,
            ha='center', va='center',
            color=YELLOW, fontsize=26, fontweight='bold')
    if subtitle:
        ax.text(W / 2, by + TBAR_H * 0.25, subtitle,
                ha='center', va='center',
                color=CYAN, fontsize=15)
    return by - 0.22


def t(ax, x, y, text, color=FG, size=16, bold=False):
    """Place text and return next-line y."""
    ax.text(x, y, text, ha='left', va='top',
            color=color, fontsize=size,
            fontweight='bold' if bold else 'normal')
    return y - size * LEAD


def hline(ax, y, color=FG, alpha=0.35):
    ax.plot([CX, W - 0.80], [y, y], color=color, lw=0.9, alpha=alpha)
    return y - 0.12


def watermark(ax):
    ax.text(CX, 0.54, 'C:\\LABELING\\>', color=SILVER,
            fontsize=10, alpha=0.40)


# ── Category data ──────────────────────────────────────────────────────────

CATS = [
    {
        'title':   'ANTHROPOMORPHIC',
        'desc':    'AI is framed as human-like — thinking, feeling, speaking, or choosing.',
        'example': '"The chatbot BELIEVES it is helping users."',
        'subs': [
            ('Cognition',     'AI thinks, reasons, or understands.',
                              '"The model REALIZES it made an error."'),
            ('Emotion',       'AI feels, wants, or cares.',
                              '"The AI FEARS it will be shut down."'),
            ('Communication', 'AI says, explains, argues, or warns.',
                              '"The assistant TELLS users to see a doctor."'),
            ('Agency',        'AI chooses, plans, refuses, or acts intentionally.',
                              '"The system REFUSES to answer the question."'),
        ],
    },
    {
        'title':   'MECHANISTIC',
        'desc':    'AI is framed as a technical system performing computational operations.',
        'example': '"The algorithm PROCESSES thousands of images per second."',
        'subs': [
            ('Data Ops',         'AI handles, filters, or transforms data inputs.',
                                 '"The model TOKENIZES the text before analysis."'),
            ('Model Lifecycle',  'AI is trained, deployed, evaluated, or updated.',
                                 '"Researchers FINE-TUNE the model on medical records."'),
            ('Output Transform', 'AI converts, produces, or restructures outputs.',
                                 '"The system TRANSCRIBES audio into written text."'),
        ],
    },
    {
        'title':   'LABOR DISPLACEMENT',
        'desc':    'AI is framed in terms of its impact on human workers and the economy.',
        'example': '"AI is REPLACING entry-level programmers."',
        'subs': [
            ('Replacement',  'AI eliminates or takes over jobs from humans.',
                             '"The software AUTOMATES tasks once done by paralegals."'),
            ('Augmentation', 'AI assists or enhances what workers can do.',
                             '"AI EMPOWERS radiologists to review more scans per day."'),
            ('Performance',  'AI outperforms, matches, or beats human benchmarks.',
                             '"The model SURPASSES expert performance on the bar exam."'),
            ('Labor Market', 'AI broadly shifts hiring, demand, or job structures.',
                             '"Automation is RESHAPING the manufacturing labor market."'),
        ],
    },
    {
        'title':   'THREAT / RISK',
        'desc':    'AI is framed as harmful, dangerous, or a source of risk.',
        'example': '"The deepfake tool DECEIVES voters ahead of the election."',
        'subs': [
            ('Direct Harm',   'AI causes tangible injury to people or institutions.',
                              '"The autonomous weapon TARGETS civilians."'),
            ('Deception',     'AI misleads, fabricates, or manipulates.',
                              '"The chatbot HALLUCINATES medical advice."'),
            ('Systemic Harm', 'AI entrenches inequality or erodes social structures.',
                              '"Facial recognition DISCRIMINATES against minorities."'),
            ('Risk Framing',  'AI poses, raises, or amplifies abstract risk.',
                              '"Experts warn that AGI POSES an existential threat."'),
        ],
    },
    {
        'title':   'TRANSFORMATION',
        'desc':    'AI is framed as driving broad change, progress, or new possibilities.',
        'example': '"AI is REVOLUTIONIZING how doctors diagnose disease."',
        'subs': [
            ('Sweeping Change', 'AI fundamentally reshapes or disrupts entire domains.',
                                '"Generative AI is REDEFINING creative industries."'),
            ('Enablement',      'AI unlocks, opens up, or makes things newly possible.',
                                '"The tool DEMOCRATIZES access to legal advice."'),
            ('Scale / Speed',   'AI accelerates, multiplies, or amplifies capacity.',
                                '"AI SUPERCHARGES drug discovery timelines."'),
            ('Improvement',     'AI upgrades, strengthens, or enriches existing things.',
                                '"The model ENRICHES personalized learning experiences."'),
        ],
    },
    {
        'title':   'GOVERNANCE',
        'desc':    'AI is framed as something regulated, overseen, or managed by institutions.',
        'example': '"The EU will REGULATE AI systems used in hiring decisions."',
        'subs': [
            ('Regulation',   'AI is subject to laws, bans, licensing, or compliance.',
                             '"Congress moves to BAN AI-generated political ads."'),
            ('Oversight',    'AI is monitored, audited, or reviewed for accountability.',
                             '"Regulators will AUDIT the algorithm for bias."'),
            ('Policy',       'AI is managed, guided, or constrained through governance.',
                             '"The White House aims to ALIGN AI with democratic values."'),
            ('Deliberation', 'Stakeholders consult, negotiate, or recommend on AI.',
                             '"Tech companies ENGAGE policymakers on safety standards."'),
        ],
    },
    {
        'title':   'EPISTEMIC TOOL',
        'desc':    'AI is framed as an instrument for producing knowledge or understanding.',
        'example': '"AI IDENTIFIES cancer markers in MRI scans."',
        'subs': [
            ('Discovery',    'AI finds, reveals, or surfaces hidden patterns or facts.',
                             '"The model UNCOVERS new drug candidates from research data."'),
            ('Analysis',     'AI examines, investigates, or interprets information.',
                             '"Researchers use AI to ANALYZE millions of social media posts."'),
            ('Verification', 'AI confirms, validates, or challenges claims.',
                             '"The tool CHECKS whether an article contains misinformation."'),
            ('Prediction',   'AI forecasts, estimates, or models future outcomes.',
                             '"The algorithm PREDICTS patient readmission risk within 30 days."'),
        ],
    },
]


# ── Render ─────────────────────────────────────────────────────────────────

with PdfPages(OUT) as pdf:

    # ── Slide 1: Title ────────────────────────────────────────────────────
    fig, ax = new_slide()
    for lw, y0 in [(2.0, H * 0.555), (0.8, H * 0.532)]:
        ax.plot([1.4, W - 1.4], [y0, y0], color=CYAN, lw=lw)
    ax.text(W / 2, H * 0.745, 'VERB FRAMING LABELER',
            ha='center', va='center',
            color=YELLOW, fontsize=44, fontweight='bold')
    ax.text(W / 2, H * 0.625, 'Research Assistant Guide',
            ha='center', va='center',
            color=FG, fontsize=26)
    ax.text(W / 2, H * 0.428, 'Verb Framing Classification Task  |  568 items',
            ha='center', va='center',
            color=CYAN, fontsize=17)
    watermark(ax)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ── Slide 2: Overview ─────────────────────────────────────────────────
    fig, ax = new_slide()
    y = header(ax, 'OVERVIEW')
    y -= 0.10

    y = t(ax, CX, y, 'This study examines how AI is described in news media.', size=16)
    y -= 0.18
    y = t(ax, CX, y, 'You will be shown one verb at a time and asked to', size=16)
    y = t(ax, CX, y, 'classify it into a CATEGORY and SUBCLUSTER.', size=16)
    y -= 0.18
    y = t(ax, CX, y, 'Think about the verb in a news headline context:', size=16)
    y = t(ax, CX + 0.5, y, '"AI [verb]s..."   or   "The algorithm [verb]s..."', CYAN, size=16)
    y -= 0.18
    y = t(ax, CX, y, 'Choose the category that best captures the role AI is', size=16)
    y = t(ax, CX, y, 'being portrayed as playing in that sentence.', size=16)
    y -= 0.26
    y = hline(ax, y + 0.10)
    y = t(ax, CX, y, 'There is no strict right or wrong answer.', YELLOW, size=16, bold=True)
    t(ax, CX, y - 16 * LEAD, 'We are collecting human judgments about intuitive meaning.', size=16)
    watermark(ax)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ── Slide 3: How to Use ───────────────────────────────────────────────
    fig, ax = new_slide()
    y = header(ax, 'HOW TO USE THE TOOL')
    y -= 0.12
    steps = [
        ('1.', 'Enter your name in the header. It is remembered across sessions.'),
        ('2.', 'A verb appears on screen.'),
        ('3.', 'Click one CATEGORY pill  (7 options).'),
        ('4.', 'Click one SUBCLUSTER pill — only those belonging to your'),
        ('   ', '    chosen category will be shown.'),
        ('5.', 'Click Submit  or press Enter  to advance to the next verb.'),
        ('6.', 'You can stop and resume at any time. Progress is saved automatically.'),
    ]
    for num, text in steps:
        ax.text(CX, y, num, ha='left', va='top',
                color=CYAN, fontsize=16, fontweight='bold')
        ax.text(CX + 0.60, y, text, ha='left', va='top',
                color=FG, fontsize=16)
        y -= 0.50

    y -= 0.16
    hline(ax, y + 0.10)
    t(ax, CX, y, 'You are done when all 568 verbs have been labeled under your name.',
      YELLOW, size=16, bold=True)
    watermark(ax)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

    # ── Slides 4–10: One per category ─────────────────────────────────────
    for cat in CATS:
        fig, ax = new_slide()
        y = header(ax, cat['title'], subtitle='Framing Category')
        y -= 0.08

        y = t(ax, CX, y, cat['desc'], FG, size=15)
        y -= 0.08
        y = t(ax, CX + 0.35, y, cat['example'], CYAN, size=14)
        y -= 0.20
        y = hline(ax, y + 0.08, color=CYAN, alpha=0.55)

        t(ax, CX, y, 'SUBCLUSTERS', YELLOW, size=14, bold=True)
        y -= 0.38

        for name, desc, example in cat['subs']:
            ax.text(CX, y, f'·  {name}', ha='left', va='top',
                    color=CYAN, fontsize=15, fontweight='bold')
            y -= 15 * LEAD
            y = t(ax, CX + 0.50, y, desc, FG, size=13)
            y = t(ax, CX + 0.50, y, example, SILVER, size=12)
            y -= 0.15

        watermark(ax)
        pdf.savefig(fig, bbox_inches='tight')
        plt.close()

    # ── Slide 11: Tips ────────────────────────────────────────────────────
    fig, ax = new_slide()
    y = header(ax, 'TIPS')
    y -= 0.12
    tips = [
        (FG,     'Go with your gut  —  but if unsure, take a few seconds to reflect'),
        (FG,     '    on how the word is often used in sentences that come to mind.'),
        (FG,     'Choose the category that fits how the verb makes AI sound,'),
        (FG,     '    not what AI technically does under the hood.'),
        (None,   ''),
        (FG,     'If a verb could fit multiple categories, pick the one that feels'),
        (FG,     '    most natural for how a journalist might use it.'),
        (None,   ''),
        (FG,     'Contact the research team if you have questions.'),
    ]
    for color, tip in tips:
        if color is None:
            y -= 0.18
            continue
        y = t(ax, CX, y, tip, color, size=16)
        y -= 0.06

    watermark(ax)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close()

print(f'Saved {OUT}  ({len(CATS) + 4} slides)')
