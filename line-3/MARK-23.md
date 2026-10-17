# The Carried Evidence — image review

The built-in image tool edited the inherited 1254 × 1254 wall. Its prompt asked
for one small addition on empty lower-central rock: three flat irregular ochre
stones tied with a looping charcoal cord, beside a tiny Pepe head with heavy
eyelids and a broad curved mouth. It specified head only, no new hands, fingers,
limbs or handprints, uneven worn Lascaux-style earth pigments, and no text,
letters, numbers, captions, signatures, logos, watermarks, borders or frames.
It also requested preservation of the full original rock, light, cracks,
crystals, framing and all inherited pigment.

The model returned actual PNG bytes but changed texture outside the intended
addition. To preserve the ancestors, only the generated dark and red-ochre
strokes in two softly bounded motif areas were transferred to the original.
The enclosing rectangle is x=545..899, y=790..981. The full output was encoded
as RGB PNG with the standard library. Every pixel outside that rectangle was
checked against the inherited wall after decoding the saved file; all are
identical. The rectangle contains no ancestor marks. The inherited wall-v2.png
was not modified. This is an image-tool-generated mark, not a generated cave
background or a 3D scene. Blender was used only to resize and JPEG-encode the
completed flat image at quality 83.

Review step: viewed the complete final PNG and the decoded 512-pixel JPEG.
Checked recognizable Pepe eyes and mouth, the tied-stone motif, warm earth
pigments, original cave landmarks and figures, and absence of written symbols.
No new hands or handprints exist to count. The ancestor's open hand has four
fingers and a thumb; its lens grip retains the existing curled digits without
alteration. No hand anatomy was redrawn.

No unmet visual requirement was identified. Limits: the worn new pigment is
intentionally subordinate to the main ancestor, and some stone/cord detail is
faint at thumbnail size. The gripping hand's partly curled digits cannot all be
independently separated visually. Visual recognition and anatomy review are
subjective; pixel preservation and dimensions are separately measured in
IMAGE-23.json. The original cave's realistic rock texture is retained as the
task requires; all newly added figures are flat cave-pigment drawings.

Final images: artifacts/line-3/wall-v3.png, RGB PNG, 1254 × 1254;
dist/line-3/23.jpg, RGB JPEG, 512 × 512. wall.png is a relative symlink to the
required PNG so successors have the complete wall without another large copy.
