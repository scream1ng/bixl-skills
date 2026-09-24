# Material pricing: IXL baseline first

Read `ixl-material-baseline.json` for the complete 22-row Dawborn September 2026 price list (12 sheet entries, 10 coil entries). The original workbook is `../assets/IXL-Steel-Price-Sept26.xlsx`. Cite workbook name, source sheet, row and BIXL material number in estimates. User has approved this as the baseline for exact matches and estimates of similar materials.

## Decision order
1. Explicit current user price or newer supplied price list overrides the saved baseline.
2. Exact material, finish, thickness and stock dimensions: use listed price and call it **IXL baseline**, not a live quote.
3. Close material: derive a **baseline-based estimate**, recording reference material/code, differences and arithmetic. Similar price does not prove equivalent engineering properties. For this user's budget estimates HA3PO may be a pricing proxy for HA250 of the same thickness; continue to specify HA250 for manufacture and clearly state the proxy. This is not approval to substitute stock.
4. Material substantially different or no defensible comparison: research current Australian supplier prices, preferring Victoria/Geelong, and label **online supplier price**. Seek a second comparable listing when practical; cite URLs, access dates, grade, thickness, finish, size, original price/GST, freight/minimum basis. Use an explicit proxy only if no exact match can be found. If neither research nor baseline supports a number, mark unpriced instead of inventing one.

## Meaning of close
Use same material family and surface treatment as the normal requirement. Do not extend plain mild steel pricing to stainless, aluminium, wear plate, high-strength steel, galvanised, aluminised or zincalume, or treat coating grades/weights as interchangeable. Cold rolled and hot rolled may have different premiums: use their own families. Use the explicit HA3PO-to-HA250 budget proxy above only with a label. Use listed XF400 prices for matching XF400; do not generalise to all structural or wear grades.

Same grade/thickness with another standard sheet size: estimate price by area ratio, retaining sheet-size availability as an assumption. Recalculate nesting for that actual/assumed size. Different thickness: preferably interpolate price per square metre between two same-family, same-finish baseline thicknesses, then multiply by target area. Outside the listed thickness range, permit mass scaling only when target thickness is within 25% of the nearest baseline thickness; otherwise use online research. This 25% is an estimating guardrail, not a metallurgical equivalence rule. Do not extrapolate the HU1 small cut-blank prices into full-sheet prices without allowing for a potentially different supply/cutting basis.

Area scaling: target sheet price = reference price * target area/reference area.
Mass scaling (same family/density/finish only): target price = reference price * target area/reference area * target thickness/reference thickness.
Show the calculation and rounding; do not invent a trade discount. Product availability and special surface/grade premiums can invalidate scaling. If material is recognisably non-comparable, browse instead of forcing a comparison.

## Units, age and procurement
The source does not explicitly state price units or GST. For an immediate budget use sheet-section prices as AUD/sheet excluding GST, labelled **unit/GST basis assumed pending confirmation**. Coil prices appear to be AUD/kg: keep that unconfirmed status explicit; never apply them as sheet prices or assume slitting/decoiling costs are included. Ask for unit confirmation when a coil-based result is material to the estimate, while providing a clearly conditional budget where possible. Preserve raw MOQ values and note their units are inferred.

Distinguish component order quantity from supplier stock MOQ. Allocate consumed sheet material to recurring cost by default. Where fresh procurement is required, separately show whole sheets, supplier MOQ purchase outlay and remaining stock; do not automatically charge all surplus inventory to the job or ignore MOQ. Do not assume existing inventory. Sheet quantities and yields are geometry calculations, not price-list facts.

Show September 2026 as the baseline vintage. A newer user list replaces it; do not label the saved list current market pricing indefinitely. For a quote date more than six months after the baseline month, flag age and cross-check online where feasible, without silently replacing negotiated baseline pricing. User can explicitly retain the baseline.

## Report
Keep the approved per-part tables. Add a short material basis note: **IXL baseline**, **Estimated from IXL baseline**, or **Online supplier price**, plus source and grade/unit/GST assumptions. Retain estimated setup/cycle times and user hourly rates. Do not describe source-backed material prices as verified nesting or production feasibility.
