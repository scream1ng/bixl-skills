# Large assemblies: helper agents

The user never needs to know about agents. Decide yourself whether helpers are worth it, ask once, and fall back to working alone.

## When to use helpers

Decide after inspection and the interview, when the proposal is being built. Count **custom parts**: parts this job designs or changes. Bought parts (screws, clamps, LED modules, drivers) are placed from vendor files or a standard library and do not count.

Offer helpers only when all three hold:

1. **Six or more custom parts** with real detail work (bends and flat patterns, ribs, bosses, snap fits, fins).
2. **The proposal fixes their interfaces**: each part's envelope, mounting points and fastener positions are on the board, so approval freezes them.
3. **They split into groups that touch only through those interfaces** (for example sheet metal, plastic, heat and mounting). Two to four groups; never one helper per screw-sized part.

Otherwise build everything yourself and do not mention helpers. Inspect a large supplied assembly yourself, one group of parts at a time, before the proposal.

If the host cannot run subagents (check under Host capabilities), do not ask: add one line to the approval message saying you will build the groups one at a time, and post an update after each.

## Ask once, with the approval question

Put the helper plan in the same message as the proposal approval question, after the outcome line and board link; the A/B/C choice below is that one question, so CAD delivery stays autonomous. Use the job's real counts and groups. Plain words, no agent jargon:

```
This product has 14 custom parts (38 others are bought screws, clamps and LED modules placed from vendor files).
The layout on the board fixes where each part sits and attaches, so they can be built at the same time.

I suggest 3 helpers:
- Helper A, sheet metal (6 parts): housing, back plate, 2 side panels, 2 brackets, with bends and flat patterns.
- Helper B, plastic (5 parts): fascia, diffuser frame, cable cover, 2 end caps, with walls, draft and snap fits.
- Helper C, heat and mounting (3 parts): heat sink, lamp holder, ceiling clamp.
I will place the bought parts, assemble everything, check clearances, screw access and overlaps, and make the final board.

Reply:
A. Approve, with 3 helpers: likely finishes sooner, uses more of your plan's allowance.
B. Approve, I build it all myself: takes longer, same result.
C. Change something on the board first.
```

Without a clear A, build alone. Approval of the board alone is not permission to spawn.

## Helper brief

Each helper gets, in writing: its parts' approved elements (ids, values, sources), the envelope and interface geometry (a STEP of the approved layout plus the mounting points and fastener positions as numbers), the process rules for its parts, what it must not change, and the output path (one STEP per part plus its editable build123d source, named by element id). It reports back: files, measured interface positions, checks run, and any deviation.

A helper never changes an interface. When it cannot meet one, it stops and reports; the lead decides, and asks the user only if the change departs from the approved proposal.

## Lead after the helpers

Place the bought parts, assemble, and run the checks on the whole assembly: interference, clearances, fastener and tool access, assembly order, and the mechanical layout, motion and process reviews. A helper's own checks do not replace these. Note on each element card who built it (for example, in `notes`: "Built by helper B, plastic"), then deliver as usual.
