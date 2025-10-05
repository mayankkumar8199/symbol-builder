# Symbol Builder Toolkit

A small toolkit for building symbol boards: extract symbols from source documents and arrange them on a drag-and-drop canvas. The apps are written in Tkinter and Pillow so they run on a standard Python install without extra UI frameworks.

## Features
- Drag symbols from a scrollable palette onto a large canvas and reposition them freely.
- Inspector panel lists every placed symbol with coordinates and a live scale slider.
- Keyboard shortcuts for fine control: Delete removes the selection, +/- resizes the active symbol, arrow keys drag while holding the mouse.
- Upload helper copies new PNG/JPEG/WEBP/BMP assets into the active palette folder without duplicating names.
- v12 adds unit-code text boxes, right-click context menu (duplicate, layering), and environment-aware symbol folder detection.
- extract_symbols.py converts the bundled PDF of Indian Army symbology into ready-to-use PNG cutouts.

## Repository Tour
| Path | Purpose |
| --- | --- |
| symbol_builder_app.py | First public UI with palette, canvas, and inspector basics. |
| symbol_builder_appV1.py | Iteration with cleaner dragging and palette improvements. |
| symbol_builder_appV11.py | Refined single-select workflow, Delete/scale shortcuts, clearer status bar. |
| symbol_builder_v12.py | Latest generation with text tool, context menu, duplicate & layering, smarter symbol directory resolution. |
| extract_symbols.py | Script that rips images from Finalized_Indian_army_Symbology_5.pdf into extracted_symbols/. |
| dataset/extraction_report.json | Metadata produced during symbol extraction. |
| extracted_symbols/ | Default working palette the apps load. Populate with PNG/JPEG/WEBP/BMP files. |
| 
equirements.txt | Minimal dependencies for the apps and extraction helper. |

## Getting Started
1. Create a virtual environment (recommended):
   `ash
   python -m venv .venv
   .venv\Scripts\activate
   `
2. Install dependencies:
   `ash
   pip install -r requirements.txt
   `
3. Prepare your symbol library. Drop image files into extracted_symbols/. To extract from the bundled PDF run:
   `ash
   python extract_symbols.py
   `

## Launching the Apps
Run whichever revision you want to explore:
`ash
python symbol_builder_app.py        # original experience
python symbol_builder_appV1.py      # V1 refinements
python symbol_builder_appV11.py     # V11 single-select workflow
python symbol_builder_v12.py        # latest release with text tool
`
Set SYMBOLS_DIR if your assets live elsewhere:
bash
set SYMBOLS_DIR=D:\path\to\your\symbols
python symbol_builder_v12.py
`

## Controls at a Glance
| Action | Result |
| --- | --- |
| Drag from palette | Drops a symbol (or text tool in v12) at the cursor. |
| Click symbol | Selects it and shows details in the inspector. |
| Drag selected symbol | Moves it around the board. |
| Delete | Removes the selected symbol. |
| + / - | Scales the selected symbol up or down (~15%). |
| Right-click (v12) | Opens duplicate/bring-to-front/send-to-back actions. |
| Inspector slider | Resizes the selected item with numeric feedback. |
| Inspector text field (v12) | Edit unit-code text boxes in place. |

## Managing Symbols
- The palette refreshes automatically; use the **Upload Symbol(s)** button to copy new assets into the active directory with safe renaming.
- symbol_builder_v12.py detects SYMBOLS_DIR, then ./extracted_symbols, then your legacy absolute path, so the app opens without prompts.
- Keep filenames descriptive; the UI converts underscores and hyphens into friendly labels.

## Version Highlights
| Revision | Focus |
| --- | --- |
| symbol_builder_app.py | Baseline drag-and-drop board, inspector shows positions. |
| symbol_builder_appV1.py | Improved palette sorting, smarter selection handling. |
| symbol_builder_appV11.py | Single-selection model, Delete shortcut, status updates. |
| symbol_builder_v12.py | Text boxes, context menu, duplication, smarter defaults. |

## Ideas for Future Iterations
- Export the canvas to PNG/PDF for sharing finished compositions.
- Support grouping and multi-select for faster layout tweaks.
- Add snapping guides or grid overlays to align symbology precisely.
- Wire up saving/loading board layouts as JSON to resume work later.
- 

