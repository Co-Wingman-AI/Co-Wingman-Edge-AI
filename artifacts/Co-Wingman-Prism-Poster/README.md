# Co-Wingman editable LaTeX poster

Open `main.tex` as the main document and compile with **pdfLaTeX**.
Keep all three `.tex` files and the `images/` directory together in the same
project when importing into Prism or another LaTeX editor.

## What to edit

- `content.tex`: title, author line, motivation, privacy wording, results, notes,
  and next steps.
- `architecture.tex`: native TikZ boxes, labels, connections, and AWS storage.
- `main.tex`: panel positions, typography, colors, statistic tiles, and page size.
- `images/`: original HWCOE logo, original terminal photo, and the conversation
  illustration reference. These are raster assets; illustration-internal text is
  part of the image. All surrounding text and the complete architecture are native
  LaTeX/TikZ, not a flattened poster screenshot.

The default print size is **48 x 36 inches, landscape**. The design uses a
1448 x 1086 coordinate grid with the origin at the top-left. The page is scaled
to its final size. Changing `paperwidth` and `paperheight` to another 4:3 size
preserves the proportions. Text sizes in the source are design-grid sizes and
scale with the entire poster.

The images are clipped by TikZ viewports, so their original files remain intact.
Change the clipping rectangles and image positions in `main.tex` to adjust crops.

## Build locally

```sh
pdflatex -interaction=nonstopmode -halt-on-error main.tex
pdflatex -interaction=nonstopmode -halt-on-error main.tex
```

Packages: geometry, fontenc, inputenc, helvet, graphicx, tikz, array, hyperref.
No shell escape, Python, external APIs, or system font installation is required.

## Evidence notes

Timing values come from the supplied `pause-assist-05` report. The photograph is
from a separate demonstration. Cue request completion is not a cue usefulness
measurement. AWS upload/reload remains labeled pending validation. No runtime
application code was changed for this poster.
