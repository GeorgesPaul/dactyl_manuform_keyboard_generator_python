# Live parameter GUI for the dactyl keyboard generator.
#
# The keyboard is rebuilt with the manifold3d mesh pipeline (dactylmesh) on
# every slider change, which takes tens of milliseconds, so the model follows
# the sliders live. STEP export uses the CadQuery pipeline and takes seconds;
# trigger it with the export button when the shape looks right.
#
# Run with:   uv run dactylgui.py
# Smoke test (renders one frame to a PNG and exits):
#             uv run dactylgui.py --screenshot out.png

import sys
import time
import os.path as path

import numpy as np
import polyscope as ps
import polyscope.imgui as psim

from dactylutils import Dact
import dactylmesh

# UI state, starting from the same configuration as dactcreate.py
params = {
    "nrows": 6, "ncols": 8, "centercol": 3,
    "alpha_deg": 15.0, "beta_deg": 5.0, "tenting_deg": 15.0,
    "keyboard_z_offset": 9.0,
    "plate_thickness": 0.95, "web_thickness": 3.0,
    "keycap_space": 19.0, "switch_plate_wall_thickness": 2.0,
    "use_wide_pinky": True, "show_caps": True, "show_walls": True,
    "tr_rot": [-15.0, 35.0, 10.0], "tr_loc": [-15.0, -16.0, -1.0],
    "tl_rot": [-15.0, 50.0, 10.0], "tl_loc": [-35.0, -15.0, 10.0],
}

last_build_ms = 0.0
mesh_names = []
status_line = ""

MESH_COLORS = {
    "body": (0.75, 0.75, 0.78),
    "walls": (0.55, 0.62, 0.75),
    "caps": (0.90, 0.56, 0.30),
}


def make_config():
    conf = Dact.Config(
        show_caps=params["show_caps"],
        use_wide_pinky=params["use_wide_pinky"],
        script_print_shapes=False,
        script_verbose_func=False,
        nrows=int(params["nrows"]),
        ncols=int(params["ncols"]),
        thumb_count=2,
        wall_z_offset=-15, wall_xy_offset=5,
        left_wall_x_offset=10, left_wall_z_offset=2,
        wall_thickness=2,
        switch_plate_wall_thickness=params["switch_plate_wall_thickness"],
        web_thickness=params["web_thickness"],
        plate_thickness=params["plate_thickness"],
        thumb_keys=Dact.Config.ThumbKeys(
            tr_rot=list(params["tr_rot"]), tr_loc=list(params["tr_loc"]),
            tl_rot=list(params["tl_rot"]), tl_loc=list(params["tl_loc"]),
        ),
    )
    conf.alpha = float(np.radians(params["alpha_deg"]))
    conf.beta = float(np.radians(params["beta_deg"]))
    conf.tenting_angle = float(np.radians(params["tenting_deg"]))
    conf.centercol = int(params["centercol"])
    conf.keyboard_z_offset = params["keyboard_z_offset"]
    conf.keycap_space = params["keycap_space"]
    # these are class level defaults derived from other defaults, so they do
    # not follow instance values automatically; keep them in sync here
    conf.centerrow = conf.nrows - 3
    conf.thumb_plate_length = conf.keycap_space + (7 * 2)
    return conf


def rebuild():
    global last_build_ms, mesh_names
    t0 = time.perf_counter()
    dact = Dact(make_config())
    meshes = dactylmesh.build_keyboard(
        dact, show_caps=params["show_caps"], show_walls=params["show_walls"]
    )
    for name in mesh_names:
        if name not in meshes and ps.has_surface_mesh(name):
            ps.remove_surface_mesh(name)
    for name, (verts, tris) in meshes.items():
        ps.register_surface_mesh(
            name, verts, tris, smooth_shade=False, color=MESH_COLORS.get(name)
        )
    mesh_names = list(meshes.keys())
    last_build_ms = (time.perf_counter() - t0) * 1000


def export_stl():
    global status_line
    dact = Dact(make_config())
    fused = dactylmesh.build_manifolds(dact, show_walls=params["show_walls"])
    verts, tris = dactylmesh.mesh_arrays(fused)
    filename = path.join("things", "right_gui.stl")
    dactylmesh.write_stl(filename, verts, tris)
    status_line = "Wrote " + filename
    print(status_line)


def export_step():
    global status_line
    import cadquery as cq
    print("Building STEP with the CadQuery pipeline, this takes a while...")
    t0 = time.perf_counter()
    conf = make_config()
    conf.show_caps = False  # caps are display-only
    dact = Dact(conf)
    try:
        model = dact.model_right_debug()
        filename = path.join("things", "right_gui.step")
        cq.exporters.export(w=model, fname=filename, exportType="STEP")
        status_line = "Wrote %s in %.1f s" % (filename, time.perf_counter() - t0)
    except Exception as e:
        status_line = "STEP export failed: %s" % e
    print(status_line)


def slider3(label, values, v_min, v_max):
    changed_any = False
    for i, axis in enumerate(("x", "y", "z")):
        changed, values[i] = psim.SliderFloat("%s %s" % (label, axis), values[i], v_min, v_max)
        changed_any = changed_any or changed
    return changed_any


def ui():
    changed_any = False

    psim.TextUnformatted("Rebuild time: %.0f ms" % last_build_ms)
    psim.Separator()

    for label, key, mn, mx in (
        ("Rows", "nrows", 4, 8),
        ("Columns", "ncols", 5, 9),
        ("Center column", "centercol", 2, 4),
    ):
        changed, params[key] = psim.SliderInt(label, params[key], mn, mx)
        changed_any = changed_any or changed

    for label, key, mn, mx in (
        ("Column curvature (deg)", "alpha_deg", 3.0, 30.0),
        ("Row curvature (deg)", "beta_deg", 1.0, 15.0),
        ("Tenting angle (deg)", "tenting_deg", 0.0, 40.0),
        ("Height offset (mm)", "keyboard_z_offset", 0.0, 30.0),
        ("Plate thickness (mm)", "plate_thickness", 0.6, 3.0),
        ("Web thickness (mm)", "web_thickness", 2.0, 6.0),
        ("Keycap space (mm)", "keycap_space", 17.0, 22.0),
    ):
        changed, params[key] = psim.SliderFloat(label, params[key], mn, mx)
        changed_any = changed_any or changed

    for label, key in (
        ("Wide pinky keys", "use_wide_pinky"),
        ("Show keycaps", "show_caps"),
        ("Show walls", "show_walls"),
    ):
        changed, params[key] = psim.Checkbox(label, params[key])
        changed_any = changed_any or changed

    if psim.TreeNode("Thumb keys"):
        changed_any = slider3("TR rotation", params["tr_rot"], -60.0, 60.0) or changed_any
        changed_any = slider3("TR location", params["tr_loc"], -60.0, 30.0) or changed_any
        changed_any = slider3("TL rotation", params["tl_rot"], -60.0, 60.0) or changed_any
        changed_any = slider3("TL location", params["tl_loc"], -60.0, 30.0) or changed_any
        psim.TreePop()

    psim.Separator()
    if psim.Button("Export STL (fast)"):
        export_stl()
    psim.SameLine()
    if psim.Button("Export STEP (slow)"):
        export_step()
    if status_line:
        psim.TextUnformatted(status_line)

    if changed_any:
        rebuild()


def main():
    ps.set_program_name("Dactyl generator")
    ps.init()
    ps.set_up_dir("z_up")
    ps.set_ground_plane_mode("shadow_only")
    rebuild()
    ps.look_at((20.0, -200.0, 220.0), (20.0, 10.0, 20.0))
    ps.set_user_callback(ui)

    if "--screenshot" in sys.argv:
        out = sys.argv[sys.argv.index("--screenshot") + 1]
        ps.screenshot(out)
        print("Wrote " + out)
        return

    ps.show()


if __name__ == "__main__":
    main()
