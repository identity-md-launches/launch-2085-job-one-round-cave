# Round 23: Matching Stones

[Code Witness](tools/code-witness/README.md) extends the unchanged line goal by
checking supplied Ethereum account code bytes against the account commitment
and an explicitly trusted block hash. It verifies the real 1,287-byte ZTO
runtime code offline. Nine new tests and all 44 ancestor tests passed. The
README gives reproducible demo and explicit verification commands, capture
observations, input bounds, dependencies and trust limits.

```sh
python3 -B line-2/tools/code-witness/code_witness.py demo
```

The new mark is a pair of ochre pebbles bearing matching charcoal ridges, linked
by a short dark line: supplied bytes matching a committed fingerprint. It was
made with the built-in imagegen tool, then composited only within the previously
bare rectangle x=885..1089, y=670..769. All decoded pixels outside this rectangle
are identical to the inherited wall. The earlier Pepe, both five-digit hands,
tree, leaves, roots and root-in-stone mark remain intact. No hands or stencils
were added. I inspected the full PNG and 512-pixel JPEG: Pepe remains recognizable,
and no text, numbers, captions, signatures, logos, watermarks, frames, real people
or political/hateful symbols were observed. The new charcoal ridges are simple
pictorial strokes, not writing. This is local review, not external approval.

The final PNG is RGB, 1254 × 1254, at `artifacts/line-2/wall.png` and the required
separate output `artifacts/line-2/wall-v3.png`. The named output remains untracked for
the delivery daemon. The continuation `wall.png` is a relative symlink to that
output, following the gathering bundle-repair precedent to avoid duplicate
image payload. Restoring the named output beside it resolves the full PNG. `dist/line-2/23.json` hashes those final PNG bytes, and
`dist/line-2/23.jpg` is a 512 × 512 color JPEG below 100 KB. Number 23 follows
the 22 pre-existing JSON records. No older numbered record was modified.

Limitations: generated stone texture within the added patch differs from the
ancestor; framing, lighting, cracks and every pixel outside it are preserved.
The generated joining stroke is dark rather than the chalk requested in the
prompt, but uses the permitted charcoal palette. The explicit requirement to
place a JPEG beside its JSON conflicts with the blanket ban on pictures outside
`artifacts/`; the required JPEG follows the existing beside-record layout in
`dist/line-2/`. There are no other new workspace pictures. The image service's
own default generated-output staging location was used before copying the
selected image into the required artifact path. No external visual approval
was obtained. See `REVIEW-23.json` for format and preservation measurements.

## Final generation prompt

> Use case: precise-object-edit. Add one small prehistoric pictogram on bare
> rock to the RIGHT of the existing tree, around x=950..1100 y=610..790 of this
> 1254x1254 square wall: a worn red ochre oval pebble containing three short
> uneven charcoal strokes like the ridges of a shell, beside a second little
> ochre oval pebble with the same three ridges, joined by a short chalk line.
> This symbolizes matching code to its committed fingerprint. Only add this
> small mark. Preserve every existing painting pixel, recognizable Pepe with
> heavy lidded eyes and wide mouth, both his hands with exactly FIVE digits each
> (four fingers and one thumb), every tree leaf, branch, root and upper-right
> root-in-stone mark. No new hands. Preserve 1254x1254 size, cave rock, cracks,
> crystals, floor, light and framing. Earth pigments only, worn handmade marks
> with stone showing through, Lascaux cave style. No words, letters, numbers,
> symbols resembling writing, captions, logos, watermarks, signatures, borders,
> frames, real people or political symbols. Save final PNG to
> artifacts/line-2/wall-v3.png if supported; no other saved images.
