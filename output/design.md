# Campus Customs — Dashboard Design

Design decisions for the operations board, and how each one is implemented.

This is a working record. More layout decisions will be added as the dashboard
develops.

---

## Decisions

### 1. Minimalist layout, blue and white

> I pick minimalist layout with blue & white colors (white takes 80%, blue is for
> accent/heading only) to make sure it's readable. I also set up an instruction of
> minimalistic font (Arial) with the same purpose, and I made it very specific that
> the font color should be in contrast with the background color.

**Why:** readability. A restrained palette and a plain typeface keep attention on
the ticket, the agents' findings and the amount of money about to leave the
account — not on the interface.

**How it is implemented:**

| Decision | Implementation |
|---|---|
| White dominates | `body` is `#ffffff`; cards are white with a 1px `#e2e2e6` border rather than a fill, so panels read as structure, not colour |
| Blue is an accent only | The **only** solid navy surface is the title bar. Navy otherwise appears on primary buttons, the selected ticket, and the left edge of an approval that spends money |
| Heading navy | `#000080` exactly, as specified |
| Minimal font | `Arial, "Helvetica Neue", Helvetica, sans-serif` at `font-weight: 300` — Arial Light where the system has it, with a graceful fall back |
| Contrast with background | **Black `#000000` on white; white `#ffffff` on navy.** Those are the only two text-on-background pairings used for body text |

**The contrast rule enforced the hardest where it matters:** the title bar is the
one navy surface, and every piece of text on it — title, subtitle, the balance and
its labels — is white or a light tint. Nowhere in the dashboard is navy text placed
on a navy field, or black text on a dark one.

Secondary text uses `#4a4a4a` and `#767676` on white for hierarchy. Both still read
as dark-on-light, so the rule holds.

### 2. Ticket resolution status by colour

> I set up the ticket resolution status per-color to make sure user knows the
> current progress easily (red if it's not yet finished, yellow for in progress,
> green for closed ticket).

**Why:** the board's most important question — *is this done?* — should be
answerable at a glance, without reading.

**How it is implemented:**

| State | Colour | Shown when | Label |
|---|---|---|---|
| **Not resolved** | Red `#b3261e` | Ticket is `open`, `pending` or `blocked`, and no run is active | "Not resolved" |
| **In progress** | Yellow `#8a6a00` | A run is live for that ticket (`queued` or `running`) | "Agents working" |
| **Resolved** | Green `#1b7a3d` | Ticket status is `closed` | "Resolved" |

**Carried in two places, not one.** Each state appears as a badge *and* as the
colour of the ticket's left border, so the board can be scanned down the edge
without reading any labels.

**Colour is never the only signal.** Each badge carries a text label beside a
coloured dot, so the state survives colour-blindness and a greyscale print.

**The yellow dot pulses**, and only while a run is actually live. Motion is
reserved for the one state that is genuinely changing; a static board has no
animation at all.

**A note on what "resolved" means here.** Green requires the ticket's status to be
`closed`, and the backend refuses to close a ticket whose outcome it cannot verify
— unpaid invoice, insufficient stock, or an unapproved price override. So green on
this board means *verified done*, not *the agents said they finished*. A ticket
that has been fully worked but still needs a human stays red, which is the honest
signal.

---

## Supporting choices made while building

These were not specified, and are recorded so they can be changed.

**The balance flashes when it changes.** Approving a payment and the money leaving
the account are otherwise two unconnected events on screen. A brief amber flash on
the balance ties the click to the consequence.

**Backend refusal text is shown word for word.** When a payment is refused the API
explains why — *"holds $160.00 and this would spend $264.00, leaving $-104.00"* —
and that is far more useful than a generic failure message, so it is surfaced
unchanged.

**Each approval says what it will do before it is clicked.** A restock PO spends
cash; a price override authorises a price; a customer draft is released for a human
to send and is never sent automatically. Those differences are written on the card,
not left to be inferred.

**Agent activity reads as a record, not a chat.** Each row is the agent's name, the
round, a one-line summary, and the tools it actually called. A tool that failed is
marked in red, and anything the agent could not determine is shown rather than
hidden — the point of the panel is auditability.

---

## Layout

```
┌──────────────────────────────────────────────────────────┐
│  NAVY TITLE BAR          white text        Checking $…   │
├────────────────┬─────────────────────────────────────────┤
│  Tickets       │  Selected ticket + Run button           │
│  (left rail)   │  What the team concluded                │
│  status colour │  Agent activity                         │
│  on each edge  │  Awaiting your approval                 │
└────────────────┴─────────────────────────────────────────┘
```

Two columns on desktop, collapsing to one below 900px. The ticket rail is fixed at
330px so the reading column keeps a comfortable measure.

---

## Still to decide

Further layout and interaction improvements are expected. Nothing below is settled:

- Whether the approval queue belongs in the main column or its own panel
- Whether completed runs should be browsable after the fact
- Whether the Cash and Reflections views from `desk_tickets.html` should appear here
