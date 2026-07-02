# dactyl_manuform_keyboard_generator_Python

This is a fork of the Dactyl Manuform keyboard generator by joshreve: https://github.com/joshreve/dactyl-keyboard
This code should be slightly more organized and easier to use. In progress

# Status

![](renders/state.png)

# How to use

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/). Dependencies are managed through `pyproject.toml` / `uv.lock`, so there is nothing to install manually; uv creates the virtual environment, fetches the pinned Python version and all packages on first run.

## Live preview GUI

```
uv run dactylgui.py
```

Opens a 3D viewer with sliders for rows, columns, curvature, tenting, thumb key placement and more. The model rebuilds in about 50 ms on every slider change, so it follows the sliders live. Use the buttons to export the current shape as STL (instant, from the mesh pipeline) or STEP (slower, through CadQuery).

## STEP file generation

```
uv run dactcreate.py
```

Generates the keyboard STEP files in /things. Modify dactcreate.py to your liking to get to the exact keyboard STEP file that you want:

    conf1 = dactylutils.Dact.Config(show_caps = True,
                                    nrows     = 5,
                                    ncols     = 6,
                                    )

You can find more configuration options under the Config @dataclass in the dactylutils.py file.

# Architecture

There are two geometry pipelines that share the same layout math (the point functions in `dactylutils.py`), so they always produce the same keyboard:

- `dactylmesh.py` builds triangle meshes with [manifold3d](https://github.com/elalish/manifold). Mesh booleans and convex hulls take milliseconds, which is what makes the live GUI possible. Also used for STL export.
- `dactylutils.py` builds B-rep solids with [CadQuery](https://github.com/CadQuery/cadquery) / OCCT. Slower, but produces proper CAD data (STEP) for further work in CAD programs.

GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007
