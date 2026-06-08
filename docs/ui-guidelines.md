# ResearchOS — UI Design Guidelines

## Design Philosophy

ResearchOS is a **premium research workspace**, not a developer dashboard.
The interface should feel like opening a well-designed academic notebook —
clean, focused, and built for long reading sessions.

**Design DNA**: Notion's clarity · Perplexity's focus · Linear's polish

---

## Color System

### Light Theme (Primary)

```
Background         #FFFFFF    Pure white — main canvas
Surface            #F9FAFB    Off-white — cards, panels (gray-50)
Surface Elevated   #FFFFFF    White — modals, popovers (with shadow)
Border             #E5E7EB    Subtle gray (gray-200)
Border Subtle      #F3F4F6    Barely-there dividers (gray-100)

Text Primary       #111827    Near-black — headings, body (gray-900)
Text Secondary     #4B5563    Medium gray — descriptions (gray-600)
Text Tertiary      #9CA3AF    Light gray — labels, timestamps (gray-400)
Text Disabled      #D1D5DB    Muted — placeholders (gray-300)

Accent Primary     #4F46E5    Indigo-600 — buttons, active states
Accent Hover       #4338CA    Indigo-700 — hover states
Accent Light       #EEF2FF    Indigo-50 — active sidebar, badges
Accent Text        #4F46E5    Indigo-600 — links, active labels

Success            #059669    Emerald-600
Warning            #D97706    Amber-600
Error              #DC2626    Red-600
Info               #2563EB    Blue-600
```

### Usage Rules

1. **White is the canvas.** Main content area is always `#FFFFFF`.
2. **Off-white for grouping.** Use `#F9FAFB` (gray-50) for sidebar, cards, stat blocks.
3. **One accent color.** Indigo only. No violet-cyan gradients, no glowing orbs.
4. **Borders are structural, not decorative.** `1px solid gray-200`, never glowing.
5. **No glassmorphism on light surfaces.** Subtle box-shadow instead.

---

## Typography

### Font Stack

- **Primary**: `Inter` (Google Fonts) — clean, professional, excellent at small sizes
- **Monospace**: `Geist Mono` — code blocks, agent logs, technical metadata

### Scale

```
Display       text-2xl    font-semibold   tracking-tight    Page titles
Heading       text-lg     font-semibold   tracking-tight    Section headers
Subheading    text-sm     font-medium     —                 Card titles
Body          text-sm     font-normal     leading-relaxed   Paragraphs, content
Caption       text-xs     font-medium     —                 Labels, metadata
Micro         text-[11px] font-medium     tracking-wide     Badges, timestamps
```

### Rules

1. **No text smaller than 11px.** Research content must be readable.
2. **Use `font-semibold` for headings**, not `font-bold`. Lighter touch.
3. **`leading-relaxed` on body text.** Research content needs breathing room.
4. **Labels are `text-xs font-medium text-gray-500 uppercase tracking-wide`**.

---

## Spacing & Layout

- **Sidebar width**: `w-60` (240px) — slim, not imposing
- **Content max-width**: `max-w-6xl` — prevents ultra-wide line lengths
- **Page padding**: `px-8 py-8` — generous but not wasteful
- **Card padding**: `p-5` or `p-6` — consistent internal spacing
- **Section gap**: `space-y-6` — clear separation between blocks
- **Border radius**: `rounded-lg` (8px) for cards, `rounded-md` (6px) for buttons/inputs

---

## Component Patterns

### Cards

```
Background:   bg-white (elevated) or bg-gray-50 (flat)
Border:       border border-gray-200
Shadow:       shadow-sm (cards) or shadow-lg (modals)
Hover:        hover:shadow-md hover:border-gray-300 transition-shadow
Radius:       rounded-lg
```

No glassmorphism. No backdrop-blur. No glowing borders.

### Buttons

```
Primary:      bg-indigo-600 hover:bg-indigo-700 text-white rounded-md
                shadow-sm text-sm font-medium px-4 py-2
Secondary:    bg-white border border-gray-300 hover:bg-gray-50
                text-gray-700 rounded-md text-sm font-medium
Destructive:  bg-white border border-red-200 text-red-600
                hover:bg-red-50 rounded-md
Ghost:        hover:bg-gray-100 text-gray-600 rounded-md
```

No gradients on buttons. No box-shadow glow effects.

### Inputs

```
Background:   bg-white
Border:       border border-gray-300
Focus:        ring-2 ring-indigo-500 border-indigo-500
Placeholder:  placeholder-gray-400
Radius:       rounded-md
Padding:      px-3 py-2 text-sm
```

### Sidebar

```
Background:   bg-gray-50 border-r border-gray-200
Active item:  bg-indigo-50 text-indigo-700 font-medium
Inactive:     text-gray-600 hover:bg-gray-100 hover:text-gray-900
Section label: text-xs font-medium text-gray-400 uppercase tracking-wide
```

### Status Badges

```
Active/Running:    bg-indigo-50 text-indigo-700 border border-indigo-200
Completed:         bg-emerald-50 text-emerald-700 border border-emerald-200
Warning:           bg-amber-50 text-amber-700 border border-amber-200
Error:             bg-red-50 text-red-700 border border-red-200
Idle/Default:      bg-gray-100 text-gray-600 border border-gray-200
```

### Modals

```
Overlay:      bg-black/20 backdrop-blur-[2px]  (very subtle)
Container:    bg-white rounded-xl shadow-xl border border-gray-200
Header:       border-b border-gray-100 px-6 py-4
Body:         px-6 py-5
Footer:       border-t border-gray-100 px-6 py-4 flex justify-end gap-3
```

---

## Scrollbar

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #D1D5DB; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }
```

---

## Shadows

```
shadow-sm:    0 1px 2px rgba(0,0,0,0.05)           Cards, buttons
shadow-md:    0 4px 6px rgba(0,0,0,0.07)            Card hover
shadow-lg:    0 10px 25px rgba(0,0,0,0.08)           Dropdowns
shadow-xl:    0 20px 50px rgba(0,0,0,0.10)           Modals
```

No colored shadows. No violet/cyan glows.

---

## Anti-Patterns (DO NOT USE)

| ❌ Avoid | ✅ Use Instead |
|----------|---------------|
| `bg-[#05060e]` dark slate backgrounds | `bg-white` or `bg-gray-50` |
| `glass-panel`, `glass-card`, `glass-input` | Standard card/input patterns above |
| Gradient text (`bg-clip-text text-transparent`) | Solid `text-gray-900` |
| Glowing orbs (`.glow-orb-primary`) | No background decorations |
| Violet/cyan color gradients on buttons | Solid `bg-indigo-600` |
| `text-zinc-*` dark theme colors | `text-gray-*` light theme scale |
| `backdrop-blur(16px)` heavy blur | `shadow-sm` or `shadow-md` |
| Terminal-style monospace UI | Clean sans-serif (Inter) |
| `shadow-violet-500/20` colored shadows | Neutral `shadow-sm` |
| `animate-pulse` on UI elements | Static or subtle `transition-all` |

---

## Research-Specific Patterns

### Long-Form Content Areas

- White background, `max-w-prose` (65ch) for readability
- `text-sm leading-relaxed text-gray-800`
- Generous paragraph spacing (`space-y-4`)

### Citation Markers

- Inline: `text-indigo-600 font-medium cursor-pointer hover:underline`
- Format: `[Author, Year]` — not numbered brackets

### Agent Activity (Workflow Timeline)

- Vertical timeline with subtle left border (`border-l-2 border-gray-200`)
- Active node: indigo dot with subtle `ring` animation
- Completed: emerald check
- Pending: gray dot
- Failed: red × with error message

### Streaming Content

- Typing cursor: blinking `|` in indigo
- Content appears word-by-word with no jarring layout shift
- Container has fixed height with overflow-y-auto
