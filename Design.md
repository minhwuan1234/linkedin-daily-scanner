LinkedIn Ops — Design System & UI Guidelines

Source of truth: the current implementation in frontend/index.html and frontend/styles.css.

Note: frontend/README.md contains older layout notes (for example, “remove sidebar”) and does not fully describe the current UI. When there is a conflict, follow the current HTML/CSS implementation and this document.

1. Design Direction

The product uses a dark operations-dashboard / admin-console visual language.

The interface should feel:

dense but controlled;

technical and operational rather than marketing-oriented;

dark, restrained, and low-glare;

status-driven, with color used primarily to communicate system state;

modular, with most content grouped into bordered panels/cards;

compact, with relatively small typography and tight controls;

consistent across LinkedIn scanning, YouTube research, outreach, account management, and system health.

Avoid introducing bright white surfaces, large decorative illustrations, oversized typography, strong gradients, or consumer-app styling unless the whole product direction changes.

2. Core Design Tokens

The existing CSS variables are the primary design tokens and should be reused before adding new hard-coded values.

:root {
  --bg: #090b0f;
  --bg-soft: #0d1015;
  --panel: #11151c;
  --panel-raised: #151a22;
  --panel-hover: #191f28;

  --border: #242b35;
  --border-strong: #343d4a;

  --text: #f4f6f8;
  --muted: #9ba4b0;
  --faint: #69737f;

  --accent: #7c6df2;
  --accent-hover: #9186f8;
  --accent-soft: rgba(124, 109, 242, 0.13);

  --green: #23c483;
  --green-soft: rgba(35, 196, 131, 0.12);

  --amber: #f4b740;
  --amber-soft: rgba(244, 183, 64, 0.12);

  --red: #ff6b7a;
  --red-soft: rgba(255, 107, 122, 0.12);

  --blue: #4d9eff;
  --blue-soft: rgba(77, 158, 255, 0.12);

  --radius-xl: 22px;
  --radius-lg: 16px;
  --radius-md: 12px;

  --shadow: 0 18px 48px rgba(0, 0, 0, 0.22);

  --sidebar-width: 248px;
  --content-max: 1840px;
}

Surface hierarchy

Use surfaces in this order:

--bg — page background.

--bg-soft — inputs, nested rows, compact inner containers.

--panel — primary card/panel surface.

--panel-raised — elevated panel when a stronger hierarchy is required.

--panel-hover — hover/selected surface.

Do not create many almost-identical dark hex values. Prefer the existing surface scale.

3. Color Semantics

Purple — product/action/processing

Primary accent:

active navigation;

primary buttons;

focus rings;

processing/scanning states;

selected tabs;

non-destructive emphasis.

Use:

var(--accent)
var(--accent-hover)
var(--accent-soft)

Green — healthy/success/available

Use for:

successful jobs;

healthy services;

available accounts;

completed states;

positive metrics.

Amber — warning/pending/cooldown

Use for:

waiting;

cooldown;

pending states;

warning controls;

limits approaching a threshold.

Red — error/destructive/offline

Use for:

failures;

invalid states;

login-required/offline states;

delete/kill actions;

blocking errors.

Blue — informational secondary state

Blue exists as a supporting semantic color, but it is less dominant than purple. Do not replace the purple product accent with blue.

Rule

Color should communicate state, not decorate arbitrary UI.

Normal panels stay neutral. Strong semantic colors should appear as badges, text, icons, progress, borders, and soft tinted backgrounds.

4. Typography

The UI uses Inter with system sans-serif fallbacks.

font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;

Typography character

compact;

high information density;

strong numeric metrics;

small uppercase labels for section metadata;

negative tracking for large headings;

muted/faint colors for supporting information.

Typical scale currently used

Purpose

Typical size

Page title

22–30px current layout

Drawer title

16–23px depending on component generation

Panel heading

12–15px

Main card metric

18–28px

Normal UI text

10–12px

Secondary metadata

9–10px

Eyebrow / kicker

9–10px uppercase

Table header

8–10px uppercase

Weight

800: page titles, metrics, badges, high-priority controls.

700: labels, navigation, table headers.

500–600: secondary structured content when needed.

400: descriptive body text.

Labels / kickers

Use compact uppercase labels with tracking:

color: var(--faint); /* or accent for emphasized kicker */
font-size: 9px;
font-weight: 700–800;
letter-spacing: 0.04em–0.13em;
text-transform: uppercase;

Do not use large all-caps headings for main content.

5. Page Architecture

The current desktop shell is:

┌──────────── fixed sidebar ────────────┬──────────────────────────────┐
│ Brand                                 │ sticky topbar                │
│                                      ├──────────────────────────────┤
│ Workspace navigation                 │                              │
│ Research navigation                  │ main tab content             │
│ Outreach navigation                  │                              │
│                                      │ panels / grids / tables      │
│ System navigation                    │                              │
│ Footer system indicator              │                              │
└──────────────────────────────────────┴──────────────────────────────┘

Desktop

--sidebar-width: 248px;
--content-max: 1840px;

Main content:

.app-shell {
  max-width: var(--content-max);
  margin-left: var(--sidebar-width);
  padding: 24px 28px 64px;
}

Sidebar

The sidebar is fixed and visually quieter than the main content.

Key behavior:

fixed left rail;

dark neutral background;

1px right border;

grouped navigation labels;

active item uses purple soft fill plus a purple left inset line;

lower-priority “System” group is pushed toward the bottom;

brand mark is a compact rounded square.

Topbar

The topbar is sticky on larger screens:

transparent-dark background;

backdrop-filter: blur(16px);

subtle bottom border;

title on the left;

system/worker actions on the right.

On narrow mobile layouts, it becomes static and stacks vertically.

6. Spacing System

The repo does not define spacing tokens, but repeated values show a practical spacing rhythm.

Prefer these values:

4px   micro gap / segmented controls
6px   label-to-input / compact metric spacing
8px   button groups / compact rows
10px  small card spacing
12px  common grid and row spacing
14px  compact card padding
16px  standard panel/grid gap
18px  panel headers / medium padding
20px  standard panel body padding
22px  drawer padding
24px  large page/modal padding
28px  desktop page horizontal padding

For new components, start from this scale instead of arbitrary values such as 17px, 23px, 27px, etc., unless alignment genuinely requires them.

7. Radius System

The interface is rounded, but not excessively pill-shaped.

Main containers

major panel: 22px (--radius-xl)

cards: 16px (--radius-lg)

controls / nested blocks: 9–13px

badges / state chips: 999px

Common patterns

.panel { border-radius: var(--radius-xl); }
.stat-card { border-radius: var(--radius-lg); }
.search-field { border-radius: 11px; }
.primary-button { border-radius: 13px; }
.status-badge { border-radius: 999px; }

Do not mix sharp 0–4px radii into normal product UI unless representing a special visualization.

8. Borders & Elevation

The UI relies more on borders and surface contrast than large shadows.

Default panel treatment:

border: 1px solid var(--border);
background:
  linear-gradient(180deg, rgba(255, 255, 255, 0.015), transparent),
  var(--panel);
box-shadow: var(--shadow);

Nested elements often drop the shadow and use:

border: 1px solid var(--border);
background: var(--bg-soft);

Hover state:

border-color: var(--border-strong);
background: var(--panel-hover);

Use strong shadows mainly for overlays, drawers, or modals.

9. Panels & Cards

Major panel

Use .panel as the base visual primitive.

Recommended structure:

<section class="panel">
  <header class="panel-header">
    <div>
      <p class="panel-kicker">Context label</p>
      <h2>Panel title</h2>
      <p class="panel-meta">Supporting text</p>
    </div>
    <div><!-- actions / badge --></div>
  </header>

  <div class="panel-body">
    ...
  </div>
</section>

Nested card

Nested operational items usually use:

padding: 11px–16px;
border: 1px solid var(--border);
border-radius: 9px–13px;
background: var(--bg-soft);

On hover, promote to --panel-hover and/or --border-strong.

Metric cards

Metrics emphasize numbers, not icons.

Pattern:

small muted label;

optional compact semantic icon;

large bold number;

faint supporting text.

Avoid dashboard cards with excessive chart decoration when a single number communicates the state.

10. Buttons

Primary button

Purple action for the main safe action in a context.

min-height: 42px;
padding: 0 16px;
border-radius: 13px;
background: var(--accent);
color: white;
font-size: 12px;
font-weight: 800;

Hover: --accent-hover.

Secondary / neutral controls

Use a neutral dark surface and normal border.

border: 1px solid var(--border);
background: var(--panel);
color: var(--text);

Destructive

Use red soft fill and red semantic text/border.

Do not make destructive actions purple.

Warning

Use amber soft fill and amber semantic text/border.

Interaction rules

hover can slightly raise a control (translateY(-1px)) on toolbar-type buttons;

disabled actions reduce opacity;

busy actions may use cursor: wait;

controls are generally 32–42px tall depending on hierarchy.

11. Tabs & Segmented Controls

Tabs are compact and contained.

General tab container

padding: 4px–5px;
border: 1px solid var(--border);
border-radius: 12px–15px;
background: var(--panel or --bg-soft);

Inactive tab:

transparent background;

muted text.

Active tab:

background: var(--panel-hover);
color: var(--text);
box-shadow: inset 0 0 0 1px var(--border-strong);

Sidebar navigation is a special tab variant with a left accent indicator.

12. Forms

Forms should remain visually integrated with the dark surfaces.

Inputs / selects

Typical style:

min-height: 36px–40px;
border: 1px solid var(--border);
border-radius: 9px–11px;
background: var(--bg-soft);
color: var(--text);
font-size: 10px–12px;
outline: 0;

Focus

Purple only:

border-color: var(--accent);
box-shadow: 0 0 0 3px rgba(124, 109, 242, 0.1);

Field labels

Use the same small uppercase metadata style as other operational labels.

Search field

Search is usually a bordered wrapper containing a transparent input, rather than styling the input alone.

13. Tables

Tables are a core part of the product and should optimize scanability.

Base

table {
  width: 100%;
  border-collapse: collapse;
}

Typical cell spacing:

padding: 11px–14px 12px–18px;
border-bottom: 1px solid var(--border);

Header

dark background;

faint text;

8–10px;

bold;

uppercase;

slight tracking.

Body

10–11px standard text;

important names use --text and heavier weight;

supporting details use --faint;

hover row uses --panel-hover.

Wide operational tables

Allow horizontal scrolling rather than crushing columns:

.table-wrap {
  overflow-x: auto;
}

Large workflow tables can deliberately define a min-width around 1100px+.

Truncation

Long URLs/headlines/names should use:

overflow: hidden;
text-overflow: ellipsis;
white-space: nowrap;

Do not let uncontrolled text break table geometry.

14. Badges & Status Chips

Use rounded status chips for machine/job/account state.

Base:

min-height: 24px;
padding: 0 9px;
border-radius: 999px;
font-size: 9px;
font-weight: 800;

Current mapping:

available / completed / idle     → green
processing / scanning / starting → purple
pending / cooldown               → amber
failed / error / needs_login     → red
offline / stopping               → red
disabled / unknown               → neutral

New states should map into one of these semantic families before creating a new color.

15. Progress Indicators

Progress tracks are thin and quiet.

height: 7px;
border-radius: 999px;
background: #202630;

Primary progress fill:

background: linear-gradient(90deg, var(--accent), #a49af9);

Use progress bars for actual progression, not decoration.

Spinners use the normal border color with the top edge set to --accent.

16. Drawers

Drawers are used for detail-heavy secondary workflows.

Behavior

fixed viewport overlay;

panel enters from the right;

dark backdrop;

strong left border/shadow;

header remains visually separated from scrolling content.

Visual treatment

background: #0c0f14; /* or panel-scale equivalent */
border-left: 1px solid var(--border);
box-shadow: -28px 0 70px rgba(0, 0, 0, 0.35);
transition: transform 180ms ease;

Drawer content typically uses 22px padding.

Use drawers when users need to inspect context while preserving the underlying page state.

17. Modals / Confirmation Dialogs

Destructive or confirmation actions use centered modal dialogs.

Current modal pattern:

full-screen fixed layer;

dark semi-transparent backdrop (~0.68 alpha);

backdrop-filter: blur(5px);

panel width around 520px for compact confirmation;

14px radius;

--border-strong border;

stronger shadow than standard cards;

distinct header/body/footer borders.

Modal buttons stack full-width on narrow screens.

Do not use a drawer for a short destructive confirmation.

18. Empty, Loading & Error States

Empty

Center compact muted text in the available space.

display: grid;
place-items: center;
color: var(--faint or --muted);
text-align: center;

Loading

Use:

small spinner;

muted 10–12px label;

no large skeleton animation unless the view truly benefits from it.

Error

Use a red-soft container with a red-tinted border and readable light-red text.

Keep errors operational and concise.

19. Navigation Rules

The product navigation is organized by workflow domain:

Workspace
  Overview
  Profiles
  Queue
  Accounts

Research
  YouTube Research

Outreach
  Connect & Messaging

System
  Health

When adding a new feature:

decide which workflow domain owns it;

prefer extending an existing page/workflow before adding a top-level nav item;

only add sidebar entries for durable product areas, not one-off utilities;

keep labels short enough to survive the collapsed sidebar state.

20. Responsive Behavior

The UI uses several historical breakpoints, but the dominant current layout behavior is:

>1180px

sidebar: 248px;

full labels visible;

multi-column panels allowed.

<=1180px

sidebar reduces to approximately 210px;

complex two-column workflow grids may collapse.

<=860px

Sidebar becomes an icon rail:

--sidebar-width: 76px;

Hide:

brand copy;

nav group labels;

nav text;

sidebar count labels where needed;

low-priority subtitle content.

Main content remains offset by the reduced sidebar width.

<=680px

topbar becomes static and stacks;

action groups can become full-width;

multi-column metric grids become one column or simplified grids;

workflow tabs can wrap;

pagination stacks;

complex forms become vertical.

<=560–640px

drawers may become full-width;

modal buttons stack;

summary grids become single-column.

Responsive principle

Prefer reflow → collapse → horizontal scroll in that order.

Do not shrink text to unreadable sizes merely to preserve desktop columns.

21. Interaction Motion

Motion is minimal and functional.

Currently used patterns include:

drawer slide: about 180ms ease;

progress width transition: about 0.35s ease;

spinner rotation: 800ms linear infinite;

subtle button lift on hover.

Avoid heavy spring animations, large scaling effects, or decorative page transitions.

22. Iconography

The current UI mostly uses:

small text/glyph symbols;

initials/letters in compact icon containers;

simple status dots;

minimal iconography rather than a large icon library.

For new icons:

keep visual weight small;

size around 16–18px for button icons and 24–30px icon containers;

use current semantic colors;

avoid multicolor icons;

do not introduce a new icon library only for one feature.

If an icon library is adopted later, convert the entire shell progressively instead of mixing several unrelated styles.

23. Content Style

The interface language is operational.

Good UI copy is:

short;

specific;

state-oriented;

action-oriented;

easy to scan.

Examples of appropriate concepts:

Ready
Processing
Completed
Failed
Cooldown
Needs login
Last updated
Current account
Remaining turn
Check acceptance
Start scan

Avoid marketing copy inside operational cards.

Panel descriptions may use one compact sentence when context is genuinely necessary.

24. Component Composition Rules

When creating a new screen or feature, prefer composing from the existing patterns:

Page/tab
└── panel
    ├── panel header
    │   ├── kicker + title + meta
    │   └── badge / actions
    └── panel body
        ├── stat grid / form / table / list
        └── nested bg-soft cards

Recommended primitives to reuse or mirror:

.panel

.panel-header

.panel-toolbar

.panel-kicker

.panel-meta

.primary-button

.secondary-button

.control-button

.pill

.status-badge

.search-field

.table-wrap

.state

.segmented-filter

.close-button

Do not build a visually unrelated “mini design system” inside a feature-specific class namespace.

25. CSS Architecture in This Repo

The current frontend/styles.css is a single large stylesheet with feature sections appended over time.

It uses section comments such as:

/* =========================================================
   FEATURE NAME
   ========================================================= */

Later rules sometimes override earlier generic rules. This means CSS source order currently matters.

When adding new CSS

Follow these rules:

Reuse existing tokens first.

Reuse an existing generic component class when possible.

Put feature-specific rules under one clearly named section.

Avoid inline styles in HTML/JS.

Keep state classes semantic (.is-active, .is-open, .is-healthy, etc.).

Keep [hidden] { display: none !important; } behavior intact.

Do not add broad element selectors late in the file if they can unexpectedly override earlier screens.

Prefer explicit feature scoping for feature-specific overrides.

Add responsive rules next to the feature they affect unless refactoring into a centralized responsive layer.

Check both Chrome and Safari when using newer CSS such as :has(), color-mix(), or backdrop-filter.

Important technical debt

The stylesheet is currently about several thousand lines and contains multiple generations of layout/responsive rules. For maintenance, future refactoring could split it into logical files such as:

styles/
  tokens.css
  base.css
  layout.css
  components.css
  tables.css
  overlays.css
  pages/
    overview.css
    youtube.css
    outreach.css
    health.css

However, do not perform this split casually during feature work. The current stylesheet relies on source order, so a refactor should be isolated and regression-tested.

26. New Feature Checklist

Before considering a new UI feature complete, verify:

Uses existing dark surface tokens.

Uses purple only for primary/action/processing emphasis.

Uses green/amber/red according to semantic state.

Uses Inter and the existing compact type scale.

Uses existing radii and border colors.

Main content is placed inside existing panel/card patterns.

Primary and destructive actions are visually distinct.

Inputs have purple focus treatment.

Tables preserve readability and can scroll horizontally when necessary.

Long text/URLs cannot break layout.

Empty/loading/error states are implemented.

Desktop sidebar layout works.

<=860px collapsed sidebar works.

<=680px stacked mobile layout works.

Drawer/modal behavior is usable on narrow screens.

No inline styling was added unnecessarily.

Existing CSS variables were reused before introducing new colors.

New feature CSS is scoped and grouped under a clear section comment.

UI was checked against both Chrome and Safari behavior.

27. Quick Reference

Default new panel

.my-feature-panel {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-xl);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.015), transparent),
    var(--panel);
  box-shadow: var(--shadow);
}

Default nested row/card

.my-feature-row {
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg-soft);
}

.my-feature-row:hover {
  border-color: var(--border-strong);
  background: var(--panel-hover);
}

Default field

.my-feature-input {
  min-height: 40px;
  padding: 0 12px;
  border: 1px solid var(--border);
  border-radius: 11px;
  outline: 0;
  background: var(--bg-soft);
  color: var(--text);
  font: inherit;
  font-size: 12px;
}

.my-feature-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(124, 109, 242, 0.1);
}

Default primary action

.my-feature-primary-button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid transparent;
  border-radius: 13px;
  background: var(--accent);
  color: #fff;
  font: inherit;
  font-size: 12px;
  font-weight: 800;
}

.my-feature-primary-button:hover {
  background: var(--accent-hover);
}

28. One-Sentence Design Rule

Build every new feature as a compact dark operational tool using the existing panel hierarchy, purple interaction accent, semantic status colors, restrained borders, and dense readable information layout.
