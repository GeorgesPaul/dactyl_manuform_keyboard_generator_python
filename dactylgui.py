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
    "show_left": True, "half_gap": 30.0,
    "tr_rot": [-15.0, 35.0, 10.0], "tr_loc": [-15.0, -16.0, -1.0],
    "tl_rot": [-15.0, 50.0, 10.0], "tl_loc": [-35.0, -15.0, 10.0],
}

last_build_ms = 0.0
mesh_names = []
status_line = ""
scene_lo = np.zeros(3)
scene_hi = np.ones(3)

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
    global last_build_ms, mesh_names, scene_lo, scene_hi
    t0 = time.perf_counter()
    dact = Dact(make_config())
    meshes = dactylmesh.build_keyboard(
        dact, show_caps=params["show_caps"], show_walls=params["show_walls"]
    )

    # The pipeline builds the right half. The left half is its mirror image
    # across a YZ plane placed just left of the right half, leaving half_gap
    # millimeters between the two halves.
    min_x = min(v[:, 0].min() for v, t in meshes.values())
    mirror_x = min_x - params["half_gap"] / 2.0

    new_names = []
    for name, (verts, tris) in meshes.items():
        color = MESH_COLORS.get(name)
        ps.register_surface_mesh(name + " right", verts, tris, smooth_shade=False, color=color)
        new_names.append(name + " right")
        if params["show_left"]:
            left_verts = verts.copy()
            left_verts[:, 0] = 2.0 * mirror_x - verts[:, 0]
            # mirroring inverts the face orientation, so flip the winding back
            left_tris = np.ascontiguousarray(tris[:, ::-1])
            ps.register_surface_mesh(name + " left", left_verts, left_tris, smooth_shade=False, color=color)
            new_names.append(name + " left")

    for name in mesh_names:
        if name not in new_names and ps.has_surface_mesh(name):
            ps.remove_surface_mesh(name)
    mesh_names = new_names

    # scene bounds, used to aim the camera
    lo = np.min([v.min(axis=0) for v, t in meshes.values()], axis=0)
    hi = np.max([v.max(axis=0) for v, t in meshes.values()], axis=0)
    if params["show_left"]:
        lo[0] = 2.0 * mirror_x - hi[0]
    scene_lo, scene_hi = lo, hi

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
        ("Gap between halves (mm)", "half_gap", 0.0, 200.0),
    ):
        changed, params[key] = psim.SliderFloat(label, params[key], mn, mx)
        changed_any = changed_any or changed

    for label, key in (
        ("Wide pinky keys", "use_wide_pinky"),
        ("Show keycaps", "show_caps"),
        ("Show walls", "show_walls"),
        ("Show left half", "show_left"),
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


def frame_scene():
    # aim the camera at the scene from the front and above, far enough back
    # to fit both halves
    center = (scene_lo + scene_hi) / 2.0
    extent = float(np.max(scene_hi - scene_lo))
    dist = 1.2 * extent
    ps.look_at(
        (center[0], center[1] - dist, center[2] + 0.9 * dist),
        tuple(center),
    )


def screen_size():
    # polyscope has no fullscreen switch, so size the window to the screen
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:  # not on Windows
        return 1920, 1080


def main():
    ps.set_program_name("Dactyl generator")
    width, height = screen_size()
    ps.set_window_size(width, height)
    ps.init()
    ps.set_up_dir("z_up")
    ps.set_ground_plane_mode("shadow_only")
    rebuild()
    frame_scene()
    ps.set_user_callback(ui)

    if "--screenshot" in sys.argv:
        out = sys.argv[sys.argv.index("--screenshot") + 1]
        ps.screenshot(out)
        print("Wrote " + out)
        return

    ps.show()


if __name__ == "__main__":
    main()
