# Job data (version 1)

`JOB/spec.json`, photos in `JOB/photos/`. All coordinates are fractions 0..1 of the **dressed** photo (`dressed/<key>.jpg`), x left→right, y top→bottom.

```json
{
  "version": 1,
  "revision": 1,
  "part": {"number": "36611", "name": "Tastic Luminate Heat Module", "doc_no": "A0866"},
  "format": "a3-landscape",
  "steps_per_page": null,
  "to_confirm": ["Torque for M4 screws"],
  "steps": [
    {
      "key": "remove-screws",
      "photo": "photos/IMG_0412.jpg",
      "dress": {"turn": 0, "rotate": -2.5, "crop": [0.1, 0.05, 0.9, 0.85], "light": true},
      "text": ["Remove 4× M4 screws ①", "Keep screws for step 6"],
      "callouts": [{"n": 1, "at": [0.48, 0.52], "tag": [0.15, 0.15]}],
      "marks": [
        {"type": "oval", "x": 0.4, "y": 0.45, "w": 0.16, "h": 0.14},
        {"type": "arrow", "x1": 0.7, "y1": 0.3, "x2": 0.55, "y2": 0.45},
        {"type": "rect", "x": 0.2, "y": 0.2, "w": 0.3, "h": 0.3},
        {"type": "text", "x": 0.7, "y": 0.02, "w": 0.22, "h": 0.065, "text": "611060 Instructions", "to": [0.78, 0.28]}
      ]
    }
  ]
}
```

- `part.title` (optional): shorter header text when `number - name` wraps to two header lines, which pushes the step text onto page 2. About 37 characters fits on A3 landscape. The file name always uses `name`.
- `format`: `a3-landscape` (1/2/4/8 per page), `a3-portrait` (1/2/4/6), `a4-landscape` (1/2), `a4-portrait` (1/2). If `steps_per_page` is `null`, the smallest size that fits all steps is used, up to the maximum, with more pages after that.
- `key`: stable lowercase-kebab ID. Comments refer to it, so keep it when reordering.
- `dress.turn`: 0/90/180/270 for sideways phone shots. `rotate`: ±45° fine levelling, applied before crop. `crop`: `[x0, y0, x1, y1]` of the turned and rotated photo. `light: false` skips white balance, contrast and sharpening.
- `text`: a string (one bullet) or a list of bullets. A nested list adds sub-bullets to the bullet before it: `["Pack in carton", ["611061 – Template", "611060 – Instructions"]]`. Max 4 bullets and 8 sub-bullets, ≤10 words each. ①–⑨ are optional and may only name callouts that exist. Word output is a real `-`/`o` bullet list, Century Gothic 14 pt.
- `callouts`: `n` 1–9, `at` = point on the feature (arrowhead), `tag` = where the numbered box (0.9 cm on paper) sits. Keep the tag over plain background. Max 4 per photo.
- `marks`: `oval`/`rect`/`text` use `x, y, w, h` (top-left plus size). A `text` label with `"to": [x, y]` gets a leader from its box edge to that point; use this for naming parts. `arrow`/`line` use `x1, y1 → x2, y2`, with the arrowhead at x2/y2, plus optional `target` naming what it hits (shown on the check sheet). `text` labels are 1–3 words. Colour is IXL red `#CC0000` at 2.25 pt unless `color` is set.
- Increment `revision` on every change after a preview has been shared.
