# The Counted Evidence

Citation Ledger lets a worker check a report's saved source passages together,
including changed-source passages that must be reviewed. The new mark gathers
dark and red pebbles inside an ochre loop.

Built-in image generation, using the imagegen skill, edited the inherited
wall-v11.png. Final prompt: preserve the square cave wall, ancestral drawings,
central Pepe, hands, rock, cracks, torchlight and framing; add only a small worn
motif of charcoal pebbles, one red, inside an uneven yellow ochre oval; no new
hands, text, numbers, signatures, logos or borders. The generator produced a
whole-wall edit. To preserve the ancestors exactly, finish_wall32.js transferred
only selected generated pigment from crop (721,950,195,97) to unused lower rock
within (650,1006,170,80), retaining the original stone between worn grains.
No new shapes were drawn by the exporter. The generated intermediate was
overwritten by the finished required wall, leaving no auxiliary workspace image.

I viewed the finished PNG and JPEG. The central heavy-lidded, wide-mouthed Pepe,
earlier marks, framing, light and cracks are unchanged. The existing spread hand
has five visible digits. The partly occluded gripping hand's complete digit
count cannot be confirmed; it was preserved, with no new hands or stencils.
No letters, numbers, captions, signatures, logos, borders, real people or
political/hateful symbols were seen. The new motif is small in the thumbnail.

- artifacts/line-3/wall-v12.png: 1254 × 1254 RGB PNG, required output.
- artifacts/line-3/wall.png: relative continuation symlink to wall-v12.png.
- dist/line-3/32.jpg: 512 × 512 JPEG, 76,399 bytes.
- dist/line-3/32.json: the sole new numbered record, bound to the PNG SHA-256.

Exactly 4,627 pixels changed within the new rectangle, zero outside. All image
measurements and the inherited digit-count limitation are in IMAGE-32.json.
GOAL.md, all ancestor tools, and all 31 older numbered records are unchanged.

Run the working piece from the repository root:

```sh
python3 -B line-3/tools/citation-ledger/ledger.py demo
```
