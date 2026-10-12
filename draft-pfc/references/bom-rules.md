# BOM rules

The inspected D365 export has Type, Level, Item/Resource, Description, Operation, Cost group, Unit, Consumption per lot size and Lot size quantity. Find columns by normalized headers, not fixed positions. Some D365 sheets omit cell r coordinates: infer consecutive columns while respecting explicit coordinates when present. Refuse formulas without cached values.

## Ownership and chronology

Production/BOM rows form an ordered depth-first hierarchy. A resource at level n belongs to the nearest preceding active Production/BOM node below that level. Reject skipped levels, resources without a parent and disconnected/multiple roots. Keep duplicate item codes as separate occurrences identified by source-row keys.

Walk children before their parent operations. Type Process with MACH identifies a machine operation. Type Setup is associated evidence, not an additional box. LAB Process is operator evidence for the same route. Service is a separate outsourced stage. Ignore Surcharge for the process diagram while preserving the row in source evidence. Repeated MACH Process rows remain separate operations; review ambiguous repetition. If more than one physical operation exists within a BOM stage, retain source order provisionally and request a route if sequence is uncertain. With several operations, stage-level materials/children do not prove which operation consumes each item: retain provisional links visibly in the issues and refine before finalizing.

Known names map Laser cutter to Laser Cut Blank, Press brake to Bend, MIG/TIG/weld to Weld, Electrocoating to E'Coat and powder coating to Powdercoat. Unknown machines retain source operation/description and remain open to review. Do not invent deburr, inspection, dispatch, transportation or storage stages absent evidence. Symbols copied from the supplied form indicate categories; an inspection square does not specify a gauge, frequency or acceptance criterion.

## Items and quantities

Keep material/hardware separate from manufactured component routes. Recognize obvious stud/nut/bolt/rivet/bush hardware from Description, not numeric code patterns. Quantity is Consumption per lot size / Lot size quantity only for a clearly supported ea/each item in its owning lot. Never derive quantity from cost or sales columns.

At a Pack stage, keep carton, ribbon and labels as its packaging list rather than three independent process routes. Display carton code and units/box only for one clear carton record with positive quantity. Retain labels/ribbons in the editable spec. Mark packaging identification as provisional when a generic Workbench could mean an assembly task rather than packing.

## Example boundaries

A typical sample BOM produces a main laser → bend → weld → e-coat → pack route, with a laser-cut spacer and a weld stud feeding welding, sheet material named by gauge and size (e.g. 2.0 HA3P 2440 X 1220 SHT), and a carton consumed as 4 per 100 pieces (25 pieces/box). A blank material line with no cost can mean shared sheet; confirm the relationship. These are sample facts, never generation defaults.

The supplied reference form was A4 portrait. Its sample author, dates and part photos must not be copied into a new job. Current BOM-only input cannot regenerate accurate part pictures; omit them rather than fabricate CAD appearance.

## Calc parts table

The pre-system draft BOM from the costing (calc) workbook is a two-column block: item code then description, no headers, finished part first. `import` uses it when no D365 header row exists, taking the longest run of code/description rows that names a stage. Stage words end the description after ` - `: LASER, BEND, WELD, E-COAT, POWDERCOAT, CLINCH (PACK is the finished part). Codes starting with the finished-part code form the main route; other stage rows form side routes grouped by description prefix (e.g. `…-3 - SPACER - LASER`). Within a route, longer codes come first because their letters list the remaining stages (`LBWE` → `BWE` → `WE` → `E`); a mismatch between the first letter and the described stage is an issue.

Rows without a stage word: carton/label/pallet rows are packaging on the Pack box (units per box only from an explicit `(25pcs/box)`); stud/nut/bolt/rivet rows are hardware; others are material feeding every laser stage. The table has no quantities or joining stages, so these stay TBC and are review issues: side routes and hardware join the main route at Weld (clinch hardware at Clinch first), otherwise the last process; shared material across several laser parts is flagged. Operation numbers are proposed 10, 20, 30… per route.
