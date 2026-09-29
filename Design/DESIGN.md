# NetConfig — Design System

Professional Network Operations Console for configuring Cisco Router/Switch via web UI.

## Overview

- **Type:** Web Application (Desktop-first, Responsive)
- **Theme:** Light (default), Dark Mode (future), Terminal always dark
- **Audience:** Network Engineering students, educators
- **Purpose:** Demo + practical use for Cisco device configuration without manual CLI

---

## Color Tokens

### Core Palette

| Token | Hex | Usage |
|---|---|---|
| `--sidebar-bg` | `#0F172A` | Sidebar background (Navy) |
| `--sidebar-text` | `#94A3B8` | Sidebar inactive text |
| `--sidebar-active` | `#1E293B` | Sidebar active link bg |
| `--sidebar-hover` | `#1E293B` | Sidebar hover link bg |
| `--bg` | `#F8FAFC` | Main background (Slate) |
| `--surface` | `#FFFFFF` | Cards, tables, panels |
| `--fg` | `#0F172A` | Primary text |
| `--muted` | `#64748B` | Secondary text |
| `--border` | `#E2E8F0` | Borders, dividers |

### Action Colors

| Token | Hex | Usage |
|---|---|---|
| `--accent` | `#2563EB` | Primary action (Blue) |
| `--accent-soft` | `#DBEAFE` | Primary action bg tint |
| `--cyan` | `#0891B2` | Secondary network accent |
| `--cyan-soft` | `#CFFAFE` | Cyan bg tint |

### Status Colors

| Token | Hex | Meaning | Must pair with |
|---|---|---|---|
| `--green` | `#16A34A` | Connected / Up / Success | Icon + Text |
| `--red` | `#DC2626` | Error / Down / Failed | Icon + Text |
| `--amber` | `#D97706` | Warning / Checking / Pending | Icon + Text |
| `--gray` | `#64748B` | Unknown / Disabled | Icon + Text |

> **Rule:** Never use color alone to convey status. Always pair with icon + text.

### Terminal (Always Dark)

| Token | Hex |
|---|---|
| `--terminal-bg` | `#0B1120` |
| `--terminal-text` | `#E2E8F0` |
| `--terminal-border` | `#1E293B` |

---

## Typography

| Font | Usage |
|---|---|
| Noto Sans Thai / IBM Plex Sans Thai | UI body text, all labels |
| JetBrains Mono | CLI, code blocks, terminal, monospace data |

### Type Scale

| Token | Size |
|---|---|
| `--fs-xs` | 12px |
| `--fs-sm` | 13px |
| `--fs-base` | 14px |
| `--fs-md` | 15px |
| `--fs-lg` | 16px |
| `--fs-xl` | 18px |
| `--fs-2xl` | 22px |

---

## Layout

### Desktop (1280px+)

```
┌──────────┬──────────────────────────────────────────┐
│          │  Topbar (sticky, blur backdrop)           │
│  Sidebar │──────────────────────────────────────────│
│  240px   │  Content Area                             │
│  (nav)   │  24px padding                             │
│          │                                           │
└──────────┴──────────────────────────────────────────┘
```

- Sidebar: fixed left, Navy `#0F172A`, 240px default
- Collapsible to 64px (icon-only) via toggle button in topbar
- State persisted to localStorage
- Transition: 0.2s ease

### Tablet (768px–1024px)

- Sidebar hidden by default, slides in as overlay via hamburger
- Content: full width, 16px padding

### Mobile (< 768px)

- Not fully designed (Desktop-first app)
- Not a target platform

---

## Sidebar

### Items

| Item | Icon | Badge | Status |
|---|---|---|---|
| Nodes | Grid | Count | Active |
| Command History | Clock | — | Active |

### Collapsed State

- Width: 64px
- Brand text hidden, shows "NC"
- Nav links: icon only, badge moves to top-right corner
- Footer version hidden

---

## Topbar

- Sticky, frosted glass (`backdrop-filter: blur(12px)`)
- Left: Toggle button + Page title + Breadcrumb
- Right: Status indicators
- Breadcrumb "Nodes" is clickable → back to Dashboard

---

## Components

### Buttons

| Class | Style |
|---|---|
| `.btn-primary` | Blue fill `#2563EB`, white text |
| `.btn-secondary` | White fill, border |
| `.btn-danger` | Red fill `#DC2626`, white text |
| `.btn-ghost` | Transparent, muted text |
| `.btn-sm` | Compact padding |
| `.btn-icon` | Square icon-only |

### Badge

| Class | Color |
|---|---|
| `.badge-green` | Green (Connected/Up) |
| `.badge-red` | Red (Error/Down) |
| `.badge-amber` | Amber (Checking/Warning) |
| `.badge-gray` | Gray (Unknown/Disabled) |
| `.badge-blue` | Blue (Info) |

Badge always includes `.badge-dot` (colored dot) + text label.

### Card

- White background, 1px border, 12px radius, subtle shadow
- 20px padding

### Input / Select

- 9px 12px padding, 1px border, 8px radius
- Focus: blue border + blue ring shadow
- Select: custom chevron SVG, no native arrow

### Table

- `.table-wrap`: white bg, border, 12px radius, overflow hidden
- `.ds-table`: headers uppercase, muted, 12px; cells 14px, 12px 16px padding
- Row hover: subtle gray bg

### Toggle (Switch)

- 40×22px, pill shape
- Off: gray `#CBD5E1`
- On: green `#16A34A`
- Thumb: 18px white circle with shadow

### Dialog (Modal)

- Overlay: `rgba(0,0,0,0.4)`
- Panel: white, 12px radius, 420px width max
- Actions: right-aligned buttons
- Triggered by: Delete, Save Config, Remove Protocol

### Command Preview Dialog

- Centered in the viewport, maximum width 672px
- Used for: Command Preview only
- Header + scrollable body + footer actions

### Toast

- Fixed bottom-right, dark bg
- Slide-in animation
- Border-left color indicates type (green/red)

---

## Screens

### 1. Nodes Dashboard (`index.html`)

**Views:**
- Card View (grid of node cards)
- Table View (data table)

**Features:**
- Search by hostname/IP
- Filter by status (Connected, Unreachable, Checking, Unknown)
- Add Node button → navigates to Add Node Wizard
- Node card shows: hostname, IP, protocol, status badge
- Empty state when no nodes exist

**Node States:**
| State | Badge | Icon |
|---|---|---|
| Connected | Green | Check circle |
| Unreachable | Red | X circle |
| Checking | Amber | Loader |
| Unknown | Gray | Help circle |

### 2. Add Node Wizard (`add-node.html`)

**3-Step Flow:**

1. **Device Info** — Enter device alias and type
2. **Protocol** — Select SSH, Telnet, or Serial; SSH/Telnet can open Scan Network
3. **Test & Save** — Test Ping → Port → Login → Read Hostname first; enable Save Node only when all required checks pass

**Features:**
- Step indicator (numbered, not colored dots)
- Each step validated before proceeding
- Back/Cancel at any step
- Test results shown per step with pass/fail icons
- Node is never persisted when the pre-save connection test fails; show the failure and offer Retry/Back
- Telnet username is optional because IOS VTY may be configured for password-only login; SSH still requires username/password
- Serial console username and password are optional because a local console may open directly at the IOS prompt
- Selecting Serial loads the currently available COM/tty ports from the machine running the backend. The list refreshes while this step is open and has a manual Refresh action; each option shows the port, device description, and a USB label when detected. USB ports appear first. Loading, error, and empty states explain what happened. The user can enter a port manually when discovery is unavailable. Listing never opens a port or creates a Node; Test Connection is still required before Save.
- **Scan Network** appears only for SSH/Telnet and opens a standard centered dialog. It accepts a valid IPv4 subnet up to `/28`, probes only TCP 22/23 without login, and shows an error, empty, loading, or result state.
- Choosing **Use SSH** or **Use Telnet** fills the Protocol form host/port, selects the matching transport, and closes the dialog. Close, backdrop, and Escape dismiss it without changing the form; serial has no network scan.

### 3. Node Detail (`node-detail.html`)

**Sticky Header:**
- Hostname, IP, Protocol, Status badge
- Actions: Save Config, Disconnect, Reconnect
- Back breadcrumb ← to Nodes Dashboard

**Tabs:**

| Tab | Content |
|---|---|
| Interfaces | Interface table with IP, Mask, Status, Protocol, Method and an Admin State toggle at the end of each row. Toggle creates a preview for Shutdown/No Shutdown; Apply remains explicit in the preview dialog. Configure Interface remains inline; other configuration profiles open in a dialog popup. |
| Routing | Protocol selector (OSPF/RIP/EIGRP/BGP/Static). Network tables with inline edit/delete. Add Network form. |
| Show | Shortcut buttons grouped by category (Interfaces, Routing, System). Raw + Table view. Copy, Clear, timestamp. |
| CLI | Dark terminal with prompt. Command history via arrow keys. Copy, Clear, Disconnect buttons. |
| Command History | — (separate page) |

Router nodes show all four tabs. Switch nodes omit **Routing** because routing-protocol forms are
outside the switch workflow; their L2/L3 port and VLAN tasks remain under Interfaces. If a node
role changes while Routing is active, the UI returns to Interfaces instead of leaving hidden
content selected.

Interface configuration must load the current interface names from the device with
`show ip interface brief` when the Interfaces tab opens. The Interface field is a select,
not free text; each option shows interface name, current IP and link status. Refresh reloads
the options, while loading/error/empty states disable Preview to prevent stale interface names.

The interface table ends with an **Admin State** toggle. Its initial state is derived from
`administratively down` in the device output; clicking it creates a typed admin-state preview
(`interface` + `shutdown`/`no shutdown`) without changing IPv4 or description. The user must
confirm Shutdown when applying the preview. The toggle is disabled while the preview is loading
and the table refreshes after a successful apply.

### Interface extensions — Phase 5

The Interfaces tab keeps the existing inventory table and **Configure Interface** form inline for
an interface that already exists. A compact **Additional Configuration** launcher opens all other
forms in a centered dialog: Loopback for every node, plus L2 Access Port, L3 Routed Port, and
VLAN/SVI for nodes saved as Switch. The dialog closes with its close button, backdrop, or Escape;
opening/closing it never sends commands. Preview closes the dialog and opens the common command
preview dialog.

The Loopback dialog lets a user enter a non-negative
Loopback number, IPv4 address, subnet mask, optional description, and administrative state. The
number is intentionally not sourced from the inventory because a new Loopback does not yet exist
in `show ip interface brief`. Existing Loopbacks are shown below that form and may be selected for
**Remove Loopback**. Create and remove open the same command-preview dialog; Apply remains an
explicit action, and removing a Loopback requires a confirmation. Neither action writes NVRAM.

Above the interface forms, a compact **Device capability** status reports support discovered by
server-side read-only commands: Switchport and VLAN. It uses an icon plus text rather than a
node-name heuristic. The Switchport status and L2/VLAN/SVI controls appear only for a node saved as
**Switch**; the server still verifies actual capability before preview rather than trusting that UI
label. Router screens omit Switchport rather than showing an unsupported state. This status never
runs a configuration command.

#### Interface profile flows

The capability result and per-interface switchport state select the profile; the browser never
infers one from an entered name.

| Profile | Typed inputs | Preview commands | Guardrail |
|---|---|---|---|
| Router IPv4 | Existing interface, IPv4/mask, description, admin state | `interface`, `ip address`, description, shutdown state | Existing inventory select only; no switchport controls. |
| L3 routed port | Existing switchport-capable interface, IPv4/mask, description, admin state | `interface`, `no switchport`, IPv4, description, shutdown state | Warning and explicit confirmation before Apply. Restore sends `no ip address` then `switchport`; it does not restore VLAN/trunk/description/admin state. |
| L2 access port | Existing physical interface, VLAN ID, description, admin state | `interface`, `switchport mode access`, `switchport access vlan`, description, shutdown state | Available only when current switchport state is Enabled; VLAN ID must be 1–4094. |
| VLAN/SVI | VLAN ID/name plus SVI IPv4/mask, description, admin state | VLAN resource commands and separate `interface Vlan<ID>` commands | Create/remove resources are distinct. Delete requires confirmation and must state whether VLAN/SVI exists. |

Every profile uses the common command-preview dialog and result/history states. A profile remains
disabled while capability or interface inventory is loading, unavailable, or stale. The L3/L2
configuration forms have a visible warning icon plus Thai explanatory text, not colour alone.
After selection, the backend reads `show interfaces <selected-interface>` and prefills the
current IPv4 address, dotted-decimal subnet mask, description and administrative state.
Preview stays disabled while this current-state read is pending.

When Apply returns an overall **success**, the preview dialog shows the per-command result briefly,
refreshes the relevant inventory/state, then closes itself automatically. A failed or partial result
stays open so the user can read the error and take recovery action.

### 4. Command History (`history.html`)

**Table:**
- Columns: Time, Node, Command Type, Status
- Expandable rows: full command and per-command result first; correlation/operation ID is under a secondary disclosure. Details button supports keyboard
- Filter by Node hostname, Status (success, failed, partial failed), and an optional local start/end date-time (minute precision); options remain available after filtering. Reject an end before the start and count/paginate only rows in the range
- Node options come from the current Node list, including Nodes with no history. Keep deleted Nodes with history as labelled legacy options. Show the current hostname in History rows, falling back to the audit snapshot when the Node no longer exists
- Compact labelled Node/Status/start/end filters in one toolbar at desktop width, wrapping on tablet; clear filters and refresh actions
- Center the desktop content at a maximum width of 896px and use fixed table column widths so sparse rows do not stretch apart
- Show Thai action label with English command type as secondary text; date and time on separate lines for scanning
- At tablet width, show one expandable audit card per operation instead of squeezing the six-column table
- Sorted newest first, 10 rows per page with previous/next controls and total count
- Pagination controls are bordered and grouped separately from the count; previous/next icons sit inline with their labels, disabled states are visible. Center the Details header and each Details button on the same column axis
- Include explicit Show commands in audit; loading/error/empty states and copy feedback are visible
- Audit is append-only: replace mock Clear History button with non-destructive notice

---

## Routing Tab — Enterprise Layout

### Protocol Summary Bar
- Horizontal bar showing all protocols at a glance
- Each protocol: name, status dot (green/gray), network count
- Example: `OSPF ● Active 2 networks | RIP ● Off | EIGRP ● Off | BGP ● Off`

### Protocol Tabs
- Tab bar below summary: OSPF | RIP | EIGRP | BGP | Static
- Each tab shows: protocol icon, status dot, network count badge

### Protocol Detail View (per tab)
- **Header:** Protocol icon + name + status + action buttons (Remove Protocol)
- **Network Table:** Editable table with columns per protocol
  - OSPF: Network, Wildcard, Area, Status, Actions (Edit/Delete)
  - RIP: Network, Status, Actions
  - EIGRP: Network, Wildcard, Actions
  - BGP: Network, Subnet Mask, Actions
- **Inline Add Form:** Grid layout, contextual fields
- **Edit Mode:** Edit banner shows "Editing network entry X" + pre-filled form + Update/Cancel

### Static Routes
- Table: Destination, Mask, Next Hop, Type, Actions
- Inline add form at bottom

### Command Preview (Centered Dialog)
- Line numbers, monospace font
- Copy All Commands
- Cancel / Apply buttons
- Per-line success/error results after Apply
- Device messages like `% Invalid input detected`

---

## UX Principles

1. **Command Preview before every Apply** — mandatory, not optional
2. **Preview ≠ Apply** — two separate steps
3. **Apply disabled until form valid** — on blur + on Preview
4. **Form validation** — on blur and on Preview click
5. **Loading / Success / Error / Empty states** — always shown clearly
6. **Confirmation Dialogs** — for Shutdown, Delete Node, Write Memory, Remove Protocol
7. **Error messages** — human-readable + raw CLI error option
8. **Keyboard** — Tab, Enter, Escape throughout
9. **Status = Color + Icon + Text** — never color alone
10. **No emojis** in UI
11. **Icons restrained** — text labels preferred, no icon overload
12. **Consistent navigation** — sidebar + back breadcrumb across all pages

### Content and help text

- Use concise, professional Thai for guidance, empty/error states, and action outcomes. Keep Cisco terms such as Interface, VLAN, Preview, Apply, and protocol names when they help users match the device workflow.
- Explain **what the section shows**, **what the next action does**, and **whether that action changes the device**. Avoid implementation-only wording such as “backend validation” in the primary explanation.
- Dashboard and Node Detail must clarify that Connected/Unreachable reflect the **latest check**, not a permanently open session. History must clarify that records are past operations, not current device configuration.
- Add Node guidance follows the actual wizard: Device Info collects alias/type; Protocol collects endpoint or local Serial port; Test & Save verifies access before persistence. For Serial, do not imply Ping/TCP port checks are required.
- Configuration forms must state that Preview only displays generated commands; Apply is the explicit device-changing step. Save Config is separate from Apply and writes the running configuration to startup configuration.
- Error and empty states should name the failed or missing resource and provide a practical next step. Status remains icon + color + text, and guidance must remain legible at desktop and tablet widths.

---

## Sample Data

| Hostname | IP | Type | Protocol | Status |
|---|---|---|---|---|
| R1 | 192.168.1.11 | Router | Telnet | Connected |
| R2 | 192.168.1.12 | Router | SSH | Connected |
| SW1 | 192.168.1.13 | Switch | Telnet | Unreachable |
| R3 | 192.168.1.14 | Router | Serial COM3 | Unknown |

---

## File Structure

```
netconfig/
├── DESIGN.md          ← This file
├── index.html         ← Nodes Dashboard
├── add-node.html      ← Add Node Wizard (3 steps)
├── node-detail.html   ← Node Detail (all tabs + drawers + dialogs)
└── history.html       ← Command History
```

---

## Tech Stack (Target Implementation)

- React 18
- Vite
- Tailwind CSS
- Lucide Icons
- shadcn/ui components

---

## Anti-Patterns (Avoid)

- Marketing/dashboard style gradients
- Emoji icons
- Generic card stacks
- Color-only status indicators
- Hero/landing page (app goes straight to functionality)
- Warm beige/peach/pink backgrounds
- Mobile-first layout (this is desktop-first)
- Scaling desktop to mobile without redesign
