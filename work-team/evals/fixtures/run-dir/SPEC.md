# Trellis — SPEC

## 1 Purpose
- Trello clone, botanical theme. Kanban usability is mandatory; theming is decoration on top.
- Stack (fixed): Vite + React 18 + TS, Vitest + RTL + jsdom, localStorage persistence, @dnd-kit DnD, CSS/framer-motion animation, `prefers-reduced-motion` respected.

## 2 Botanical vocabulary

| Trello term | Trellis term |
|---|---|
| Board | Garden |
| List | Bed |
| Card | Seedling |
| Archive (action) | Compost |
| Archived item | Composted |
| Restore (action) | Replant |
| Label | Tag Bloom |
| Checklist | Growth chart |
| Checklist item | Task shoot |
| Comment/activity log | Journal entry |
| Board background/theme | Season |
| Due date | Bloom-by date |
| Search/filter | Prune (filter view) |

UI copy uses Trellis terms; code identifiers use plain Trello-equivalent English (Board/List/Card) — no botanical names in code, only in user-facing strings.

## 3 Data model

```ts
// schema version — bump on breaking shape change, write migration
const SCHEMA_VERSION = 1;

type ID = string; // uuid v4

interface Garden { // Board
  id: ID;
  title: string;
  season: SeasonId; // background/theme
  createdAt: string; // ISO
}

interface Bed { // List
  id: ID;
  gardenId: ID;
  title: string;
  order: number; // fractional index, see Ordering
  archived: boolean;
}

// Note: no Garden.archived — brief requires archive/restore for beds and
// seedlings only, not gardens.

interface Seedling { // Card
  id: ID;
  bedId: ID;
  title: string;
  description: string;
  order: number; // fractional index within bed
  tagIds: ID[];
  dueDate: string | null; // ISO date
  checklist: TaskShoot[];
  journal: JournalEntry[];
  archived: boolean;
  archivedByBed: boolean; // true if archived via bed compost cascade, not directly — see FR-13
  createdAt: string;
}

interface TaskShoot { // checklist item
  id: ID;
  text: string;
  done: boolean;
}

interface JournalEntry { // comment/activity
  id: ID;
  type: "comment" | "activity";
  text: string; // comment text, or activity description
  createdAt: string;
}

interface TagBloom { // Label
  id: ID;
  gardenId: ID;
  name: string;
  color: string; // hex or theme token
}

type SeasonId = "spring" | "summer" | "autumn" | "winter"; // theme presets

interface TrellisState {
  version: number;
  gardens: Garden[];
  beds: Bed[];
  seedlings: Seedling[];
  tags: TagBloom[];
}
```

- **IDs**: `crypto.randomUUID()`.
- **Ordering**: fractional-index float `order` per (bed within garden, seedling within bed). Reorder = recompute sibling's `order` as midpoint; renumber whole set only on float exhaustion (>~15 sig figs).
- **localStorage key**: `trellis:state`.
- **Schema**: single JSON blob = `TrellisState`, `version` field gates migrations (none at v1; unknown/missing version → treat as corrupt, reset to empty state, keep raw value under `trellis:state:corrupt:<ts>` for recovery).
- Archive = soft delete via `archived: true`, not physical deletion.

## 4 Functional requirements

**FR-1 Create garden**
- Given the garden list view, When user submits a non-empty title, Then a new Garden is created, persisted, and shown.
- Given empty/whitespace-only title, When submitted, Then rejected, no state change.

**FR-2 Create bed**
- Given an open garden, When user adds a bed with a title, Then bed appended at end of bed order, persisted.
- Given empty/whitespace-only title, When submitted, Then rejected, no state change.

**FR-3 Create seedling**
- Given a bed, When user adds a seedling with a title, Then seedling appended at end of that bed, persisted, seedling element carries `data-anim="bloom"` for the animation's duration (absent under reduced-motion).
- Given empty/whitespace-only title, When submitted, Then rejected, no state change.

**FR-4 Drag-reorder seedling within a bed**
- Given seedlings in a bed, When user drags one to a new position in the same bed, Then its `order` updates to sit between new neighbours, persisted; dragged element carries `data-anim="sway"` for the drag's duration (absent under reduced-motion).

**FR-5 Drag-move seedling between beds**
- Given seedlings in bed A, When user drags one into bed B at position N, Then `bedId` and `order` update to match, persisted.

**FR-6 Drag-reorder beds**
- Given beds in a garden, When user drags a bed to a new position, Then bed `order` updates, persisted.

**FR-7 Card detail modal**
- Given a seedling, When user clicks it, Then modal opens showing title, description, tags, due date, checklist w/ progress, journal.
- When user edits any field in modal, Then change persists on blur/submit without closing modal.

**FR-8a Manage Tag Blooms**
- Given a garden, When user creates a tag with name + colour, Then it's added to that garden's tag set, persisted, available to apply.
- Given a garden's tag set, When user edits a tag's name/colour, Then all seedlings using it reflect the change; When user deletes a tag, Then it's removed from the set and unassigned from all seedlings, persisted.

**FR-8 Tag colours**
- Given modal open, When user adds/removes a tag on the seedling, Then tag chip (with colour) reflects immediately on both modal and board card.

**FR-9 Due date**
- Given modal open, When user sets a due date, Then card shows due-date badge; overdue (`dueDate` < today, regardless of checklist state) badge visually distinct and has `data-overdue="true"`.

**FR-10 Checklist**
- Given modal open, When user adds/checks/unchecks/deletes a task shoot, Then growth-chart progress bar updates (animated fill), persisted.

**FR-11 Comments/activity**
- Given modal open, When user posts a comment, Then journal entry appended with timestamp, persisted; system also auto-logs activity entries (create/move/archive) as `type: "activity"`.

**FR-12 Archive/restore card**
- Given a seedling, When user composts it, Then `archived: true`, removed from board view after its element carries `data-anim="wilt"` for the animation's duration (skipped under reduced-motion).
- Given archive view, When user replants a composted seedling, Then `archived: false`, reappears in original bed at end of order.

**FR-13 Archive/restore list**
- Given a bed, When user composts it, Then bed `archived: true`; each currently-unarchived seedling in it gets `archived: true, archivedByBed: true` (seedlings already archived individually are left as-is).
- Given a composted bed, When user replants it, Then bed `archived: false`; only seedlings with `archivedByBed: true` are restored (`archived: false, archivedByBed: false`) — seedlings archived individually before the bed was composted stay archived.

**FR-14 Search/filter**
- Given a garden with seedlings, When user types in search box, Then only seedlings whose title/description match (case-insensitive substring) remain visible; beds with no matches shown empty (not hidden).
- Given tag filter selection, When one or more tags selected, Then only seedlings having any selected tag are visible; combines with text search (AND).

**FR-15 Board background/theme (Season) picker**
- Given garden settings, When user picks a season, Then garden's `season` updates, background/palette changes immediately, persisted.

**FR-16 Persistence across reload**
- Given any state change, When page is reloaded, Then all gardens/beds/seedlings/tags/journal restored exactly as last saved.

## 5 Theme & animation spec

| Trigger | Animation | Duration | Reduced-motion fallback |
|---|---|---|---|
| Seedling created | Bloom (scale 0.8→1 + fade + petal-pop) | 300ms | Instant fade-in, 0ms |
| Seedling composted (archived) | Wilt (rotate/droop + fade + desaturate) | 400ms | Instant fade-out, 0ms |
| Seedling dragged | Sway (subtle rotate ±3deg loop) | continuous while dragging | No sway; static lift shadow only |
| Seedling dropped | Settle (slight overshoot bounce) | 200ms | No bounce; instant snap |
| Checklist progress change | Growth-chart bar fill (vine-grow width transition) | 250ms | Instant width change |
| Bed reordered | Slide to new slot | 200ms | Instant reposition |
| Garden season change | Palette crossfade | 300ms | Instant swap |
| Modal open/close | Grow from card / shrink to card | 250ms | Instant show/hide |
| Tag added | Chip pop-in | 150ms | Instant appear |

- All durations/animations gated by `@media (prefers-reduced-motion: reduce)` — CSS media query or JS `matchMedia` check; reduced-motion path = 0ms/instant per row above.
- Testable hook: the animating element carries `data-anim="<name>"` (e.g. `bloom`, `wilt`, `sway`) for the animation's duration; attribute absent/omitted when reduced-motion is active. Applies to every row above with a named animation.

## 6 Non-functional

- **Persistence**: write-through to localStorage on every state mutation (debounced ~100ms ok); load on app init; corrupt/missing data → empty state, never crash.
- **A11y**: keyboard DnD alternative (@dnd-kit keyboard sensor) for reorder/move; focus trap in modal; `aria-label`s on icon-only buttons; colour not sole means of tag/due-date meaning (also text/icon).
- **Perf**: not covered by unit tests (jsdom has no real paint/frame timing) — verify manually/Lighthouse. Boundary-testable proxy: board with 10 beds x 50 seedlings, dragging a seedling to a new position leaves sibling seedlings' DOM node identity unchanged (same node via `data-testid`/ref, not re-created).

## 7 Out of scope
- Multi-user, auth, backend/sync, real-time collab.
- Card attachments/file upload.
- Board templates, power-ups/plugins.
- Undo/redo beyond archive-restore.
- Mobile-native app (responsive web only, no native gestures beyond dnd-kit touch support).
- Export/import.
