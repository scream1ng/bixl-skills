# Calculator input contract (version 2)

Run `python3 scripts/calculate.py INPUT.json > RESULT.json`. Use standard-library Python. Unknown fields, invalid types and missing required inputs fail; do not bypass a failure by removing relevant cost rows. Version 1 inputs must be rebuilt using the explicit component tree; there is no silent quantity migration.

## Top level and BOM

Required: `schema_version: 2`, `quantity` (positive integer finished assemblies/batch), `components` and `rows` (nonempty lists). Optional: `gross_margin` [0,1), `job`, `revision`. Margin defaults to saved 0.28; zero is valid.

Each component requires `id`, `name`, `parent_id`, `quantity_per_parent` (positive integer), `make_buy` (`make` or `buy`). Exactly one root has parent_id=null and quantity_per_parent=1. Every other node references an existing parent. Cycles and costed children under buy nodes are rejected. Use a separate occurrence ID when the same part appears beneath two parents. Multiply quantities through parents exactly once; do not place cumulative quantities in quantity_per_parent.

Buy nodes require exactly one recurring fixed purchase row, possibly unpriced. Omit supplier-internal children. A make node owns its conversion/material rows plus rolled children; never put an inclusive purchase price on a make parent. For purchased material subsequently modified, use a make component with a buy child and conversion on the make component. Every leaf requires a recurring cost or explicit unpriced row; no silent free parts.

## Common row fields

Required: unique stable `id`, `name`, `kind`, `category`, nonempty `basis`, and exactly one of `component_id` or `allocations`. Categories: material, component_processing, assembly_finish, other. `material` rows must use category material; `process` rows cannot. Fixed rows (for example purchased hardware as material) are not checked, so choose their category deliberately. Basis records source/status and assumptions; zero cost must have a deliberate explanation. Use stable IDs across revisions.

`allocations` maps component IDs to positive shares summing to 1, and is only valid for supplier_batch/shared_batch. Shares allocate the **whole batch cost**, not a per-part amount; account for differing component quantities. Otherwise cost belongs to component_id and quantity is Q × its cumulative BOM quantity.

Optional: `unpriced`, `one_off` and `absorbed_in_margin` must be literal JSON true/false, never strings. An unpriced row must omit all kind-specific fields and extra_quantity; its basis explains what is missing. Unknown is not zero. `one_off: true` separates its cost from recurring totals. Fixed one-offs use unit_price as the entire one-off charge; process one-offs use one cycle plus setup. Show unpriced one-offs separately even when recurring costs are complete. Amortization is not automatic: use a separate documented recurring allowance based on the authorized amortization volume and never also charge that same tooling upfront. A one-off material row produces no procurement scenario.

`absorbed_in_margin: true` is valid only on a priced, recurring `process` row (routine inspection/packing). Its cost is excluded from manufacturing cost, categories and BOM roll-ups and reported as `absorbed_batch_cost`/`absorbed_per_assembly`, with `effective_margin` = (selling − cost − absorbed)/selling. It does not satisfy a leaf's cost coverage.

Optional `extra_quantity` is a nonnegative integer with `extra_quantity_basis` required when nonzero. This adds units at that specific process/material/fixed row without changing finished BOM quantities or multiplying setup. Model scrap propagation explicitly: reject before coating adds material and upstream conversion, not automatically coating. Model rework as a separate process row with its total batch time via shared_batch if only some units are reworked. Do not assume this is a complete yield model. Extra quantities are invalid on one-off/shared/batch rows; include them in the documented batch calculation instead.

## Row kinds

- `process`: requires setup_h (nonnegative), setup_count (nonnegative integer), pcs_per_h (positive), cycle_seconds (map of named nonnegative seconds), cycle_basis, and exactly one of resource or hourly_rate. Resource is a saved resources key; labour and machine rates are summed once. An explicit hourly_rate requires rate_basis. Optional setup_hourly_rate overrides the run rate. Named cycle seconds must sum to 3600/pcs_per_h within 1%. A measured cycle may be one named element with its source; an estimate must break out handling and productive work, plus relevant repositioning/cleanup. Cost = setup_h × setup_count × setup_rate + (required units + extra_quantity)/pcs_per_h × run_rate.
- `material`: requires sheet_price, parts_per_sheet (positive integer), sheet_size_mm [W,L], procurement (`fresh`, `inventory`, `unknown`), stock_moq_sheets (nonnegative integer). Price basis and estimated/verified yield status belong in basis. Allocated cost = required units × sheet_price/parts_per_sheet. Output separately shows whole sheets, fresh-procurement MOQ outlay and remaining capacity. A fresh-purchase scenario is not proof that stock must be bought. If MOQ is unknown, use 0 only as an explicitly labelled no-MOQ scenario; disclose that omission.
- `fixed`: requires unit_price (nonnegative). For bought parts this is per physical purchased item. For other allowances it is per owning component. No supplier minimum fields are accepted here; use supplier_batch.
- `supplier_batch`: requires unique charge_scope (supplier/order/release identifier), lines, minimum_batch_charge and batch_fee (nonnegative, explicit). Each line requires component_id, quantity (positive integer physical units in the supplier batch), unit_price and basis. One line per component; each line's component must be the row's component_id or an allocation key, and across all recurring supplier_batch rows the line quantities for a component must total at least Q × its cumulative BOM quantity (more is allowed for scrap; separate releases may split it; one-off rows are not counted). Known limit: two different services on one component share this total, so check each service's quantity yourself. Cost = max(sum(quantity × unit_price), minimum_batch_charge) + batch_fee. Use one row for one shared minimum scope; allocate once across components. Separate shipments/releases may have separate scopes. A missing quote/minimum must be disclosed in basis or made unpriced; do not manufacture a known zero. The same physical scope cannot be entered twice.
- `shared_batch`: requires unique charge_scope and batch_cost. Optional setup_batch_cost must not exceed total. Use for shared setup/co-nest/rework costs calculated once, with arithmetic documented in basis. Allocate across components. For shared material procurement, optional procurement object requires sheet_price, consumed_sheet_equivalents, purchase_sheets (integer), basis. Cost must equal sheet_price × consumed_sheet_equivalents; purchase_sheets must cover consumption. Put co-nest conversion in a separate process/shared row. Do not also add each component's standalone sheet charge. Model different stock grades/thicknesses/sizes in separate scopes.

## Output and revisions

Output provides per-row costs, own and rolled BOM costs, setup included, category totals, recurring cost/profit/selling price, separate one-offs, absorbed cost and effective margin, procurement scenarios and unpriced IDs. The grand total is the root rolled cost, **not the sum of every BOM rolled total**. Input snapshots freeze effective resource hourly rates and gross margin for reproducible comparison, even after saved factory rates change. Never add procurement outlay to allocated manufacturing cost.

Run `python3 scripts/compare.py PREVIOUS_RESULT.json CURRENT_RESULT.json`. Report every row delta plus changed quantity/BOM/margin context; reconcile delta totals and explain the reason. Compare recurring unit costs, absorbed costs and one-off batch costs separately. If a prior result is missing, disclose missing basis and reconstruct only supported facts. Never silently choose different cycle times for a rerun. Store snapshots with a requested deliverable; otherwise retain them in working context without creating unsolicited files for the user.

## Minimal example

```json
{
  "schema_version": 2,
  "quantity": 100,
  "components": [
    {"id":"assembly","name":"Assembly","parent_id":null,"quantity_per_parent":1,"make_buy":"make"},
    {"id":"bracket","name":"Bracket","parent_id":"assembly","quantity_per_parent":2,"make_buy":"make"},
    {"id":"stud","name":"Stud","parent_id":"bracket","quantity_per_parent":2,"make_buy":"buy"}
  ],
  "rows": [
    {"id":"stud-purchase","name":"Studs","kind":"fixed","category":"other","component_id":"stud","basis":"User price AUD each ex GST","unit_price":0.85},
    {"id":"bracket-bend","name":"OP20 Bend","kind":"process","category":"component_processing","component_id":"bracket","basis":"Provisional one batch, two bends","resource":"bend","setup_h":0.25,"setup_count":1,"pcs_per_h":100,"cycle_seconds":{"handling":12,"bending":24},"cycle_basis":"Estimated total cycle"},
    {"id":"bracket-remainder","name":"Material, laser and insertion","kind":"fixed","category":"component_processing","component_id":"bracket","basis":"Incomplete example: these operations still require costing","unpriced":true},
    {"id":"assembly-weld","name":"Welding","kind":"fixed","category":"assembly_finish","component_id":"assembly","basis":"Welding not yet estimated in this input example","unpriced":true}
  ]
}
```
