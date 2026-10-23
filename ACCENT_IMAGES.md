# Images that carry the accent

Written by `tools/accent_images.py` (#86 A). Do not edit by hand: after adding or changing an image, run `python tools/accent_images.py`. `tests/test_accent_images.py` fails until this file is what the tool writes.

If the accent ever moves, the code moves it in ten lines; these images do not move with it. **shaded** art is hand-made and is remade by hand (#84). **flat** art could be recolored by swapping exact colors. A **screenshot** is retaken. A **fixture** is a test input. Accent: hue within 6 degrees of `BRAND_GOLD` or `BRAND_DARK_GOLD`, saturation and value at least 0.15; an image carries it from 1% of its pixels; flat means its three commonest accent colors cover at least 90% of them. The tool's docstring says why.

**30 images of art carry the accent, 30 of them distinct.**

| folder | files | shaded | flat | screenshot | fixture | none |
|---|---|---|---|---|---|---|
| `resources/background_images` | 1 | 1 | 0 | 0 | 0 | 0 |
| `resources/button_images` | 27 | 27 | 0 | 0 | 0 | 0 |
| `resources/icons` | 2 | 2 | 0 | 0 | 0 | 0 |
| `resources/screenshots` | 7 | 0 | 0 | 7 | 0 | 0 |

## `resources/background_images`

| file | size | accent | shades | kind | same as |
|---|---|---|---|---|---|
| `background.png` | 3840x2169 | 12.1% | 3101 | shaded |  |

## `resources/button_images`

| file | size | accent | shades | kind | same as |
|---|---|---|---|---|---|
| `clear_base.png` | 584x168 | 37.9% | 2239 | shaded |  |
| `clear_hover.png` | 584x168 | 40.7% | 2220 | shaded |  |
| `clear_pressed.png` | 584x168 | 47.4% | 2039 | shaded |  |
| `dominant_base.png` | 584x168 | 39.5% | 2153 | shaded |  |
| `dominant_hover.png` | 584x168 | 39.8% | 2178 | shaded |  |
| `dominant_pressed.png` | 584x168 | 48.0% | 2196 | shaded |  |
| `export_base.png` | 584x168 | 41.2% | 2015 | shaded |  |
| `export_hover.png` | 584x168 | 38.1% | 2015 | shaded |  |
| `export_pressed.png` | 584x168 | 47.7% | 2015 | shaded |  |
| `grab_base.png` | 584x168 | 38.4% | 2172 | shaded |  |
| `grab_hover.png` | 584x168 | 40.5% | 2186 | shaded |  |
| `grab_pressed.png` | 584x168 | 47.6% | 2195 | shaded |  |
| `reset_base.png` | 584x168 | 36.9% | 2252 | shaded |  |
| `reset_hover.png` | 584x168 | 37.3% | 2260 | shaded |  |
| `reset_pressed.png` | 584x168 | 42.3% | 2296 | shaded |  |
| `save_base.png` | 584x168 | 44.7% | 2109 | shaded |  |
| `save_hover.png` | 584x168 | 42.0% | 2109 | shaded |  |
| `save_pressed.png` | 584x168 | 50.2% | 2015 | shaded |  |
| `screen_base.png` | 584x168 | 35.7% | 2168 | shaded |  |
| `screen_hover.png` | 584x168 | 35.8% | 2298 | shaded |  |
| `screen_pressed.png` | 584x168 | 50.2% | 2244 | shaded |  |
| `settings_gear_base.png` | 512x512 | 93.4% | 3390 | shaded |  |
| `settings_gear_hover.png` | 512x512 | 92.9% | 2888 | shaded |  |
| `settings_gear_pressed.png` | 512x512 | 93.1% | 3418 | shaded |  |
| `upload_base.png` | 584x168 | 38.7% | 2387 | shaded |  |
| `upload_hover.png` | 584x168 | 38.7% | 2409 | shaded |  |
| `upload_pressed.png` | 584x168 | 46.3% | 2038 | shaded |  |

## `resources/icons`

| file | size | accent | shades | kind | same as |
|---|---|---|---|---|---|
| `app_icon.ico` | 256x256 | 81.5% | 1363 | shaded |  |
| `icon.png` | 512x512 | 81.1% | 3602 | shaded |  |

## `resources/screenshots`

| file | size | accent | shades | kind | same as |
|---|---|---|---|---|---|
| `dominant-colors.png` | 1920x1080 | 10.4% | 9458 | screenshot |  |
| `extraction.png` | 1920x1080 | 10.4% | 8720 | screenshot |  |
| `hero.png` | 1920x1080 | 14.0% | 6564 | screenshot |  |
| `palette-export.png` | 1920x1080 | 10.3% | 9048 | screenshot |  |
| `screen-picker.png` | 1920x1080 | 12.5% | 11399 | screenshot |  |
| `settings-panel.png` | 1920x1080 | 9.1% | 8594 | screenshot |  |
| `theme-mode.png` | 1920x1080 | 3.7% | 5091 | screenshot |  |
