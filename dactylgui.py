# Live parameter GUI for the dactyl keyboard generator.
#
# The keyboard is rebuilt with the manifold3d mesh pipeline (dactylmesh) on
# every slider change, which takes tens of milliseconds, so the model follows
# the sliders live. STEP export uses the CadQuery pipeline and takes seconds;
# trigger it with the export button when the shape looks right.
#
# The two halves can share one set of sliders (mirror mode, the default) or
# be configured fully independently, each with its own sliders. The pinky
# column width can be set for all rows at once or per row.
#
# Run with:   uv run dactylgui.py
# Smoke test (renders one frame to a PNG and exits):
#             uv run dactylgui.py --screenshot out.png

import copy
import sys
import time
import os.path as path

import numpy as np
import polyscope as ps
import polyscope.imgui as psim

from dactylutils import Dact
import dactylmesh

MAX_ROWS = 8  # matches the row slider maximum

# Parameters for one keyboard half, starting from the dactcreate.py defaults
HALF_DEFAULTS = {
    "nrows": 6, "ncols": 8, "centercol": 3,
    "alpha_deg": 15.0, "beta_deg": 5.0, "tenting_deg": 15.0,
    "keyboard_z_offset": 9.0,
    "plate_thickness": 0.95, "web_thickness": 3.0,
    "keycap_space": 19.0, "switch_plate_wall_thickness": 2.0,
    "wall_thickness": 2.0, "wall_flare": 5.0,
    "use_wide_pinky": True,
    "pinky_uniform": True,                 # one width for all pinky rows
    "pinky_width": 28.0,                   # used when pinky_uniform is on
    "pinky_rows": [28.0] * MAX_ROWS,       # per row widths otherwise
    "tr_rot": [-15.0, 35.0, 10.0], "tr_loc": [-15.0, -16.0, -1.0],
    "tl_rot": [-15.0, 50.0, 10.0], "tl_loc": [-35.0, -15.0, 10.0],
}

half_params = {
    "right": copy.deepcopy(HALF_DEFAULTS),
    "left": copy.deepcopy(HALF_DEFAULTS),
}

view = {
    "mirror": True,     # one set of sliders drives both halves
    "show_left": True,
    "half_gap": 30.0,
    "show_caps": True,
    "show_walls": True,
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


def left_source():
    # which parameter set drives the left half
    return half_params["right"] if view["mirror"] else half_params["left"]


def make_config(p):
    conf = Dact.Config(
        show_caps=view["show_caps"],
        use_wide_pinky=p["use_wide_pinky"],
        script_print_shapes=False,
        script_verbose_func=False,
        nrows=int(p["nrows"]),
        ncols=int(p["ncols"]),
        thumb_count=2,
        wall_z_offset=-15,
        wall_xy_offset=p["wall_flare"],
        left_wall_x_offset=10, left_wall_z_offset=2,
        wall_thickness=p["wall_thickness"],
        switch_plate_wall_thickness=p["switch_plate_wall_thickness"],
        web_thickness=p["web_thickness"],
        plate_thickness=p["plate_thickness"],
        thumb_keys=Dact.Config.ThumbKeys(
            tr_rot=list(p["tr_rot"]), tr_loc=list(p["tr_loc"]),
            tl_rot=list(p["tl_rot"]), tl_loc=list(p["tl_loc"]),
        ),
    )
    conf.alpha = float(np.radians(p["alpha_deg"]))
    conf.beta = float(np.radians(p["beta_deg"]))
    conf.tenting_angle = float(np.radians(p["tenting_deg"]))
    conf.centercol = int(p["centercol"])
    conf.keyboard_z_offset = p["keyboard_z_offset"]
    conf.keycap_space = p["keycap_space"]
    conf.keycap_pinky_space = p["pinky_width"]
    if not p["pinky_uniform"]:
        conf.pinky_row_widths = list(p["pinky_rows"][: conf.nrows - 1])
    # these are class level defaults derived from other defaults, so they do
    # not follow instance values automatically; keep them in sync here
    conf.centerrow = conf.nrows - 3
    conf.thumb_plate_length = conf.keycap_space + (7 * 2)
    return conf


def build_half(p):
    dact = Dact(make_config(p))
    return dactylmesh.build_keyboard(
        dact, show_caps=view["show_caps"], show_walls=view["show_walls"]
    )


def rebuild():
    global last_build_ms, mesh_names, scene_lo, scene_hi
    t0 = time.perf_counter()

    right = build_half(half_params["right"])
    left = None
    if view["show_left"]:
        # in mirror mode the left half reuses the right half's meshes
        left = right if view["mirror"] else build_half(left_source())

    # The pipeline builds right hand geometry. The left half is its mirror
    # image across a YZ plane placed so that half_gap millimeters stay
    # between the two halves.
    right_min_x = min(v[:, 0].min() for v, t in right.values())
    left_min_x = min(v[:, 0].min() for v, t in left.values()) if left else right_min_x
    mirror_x = (right_min_x + left_min_x - view["half_gap"]) / 2.0

    new_names = []
    for name, (verts, tris) in right.items():
        ps.register_surface_mesh(name + " right", verts, tris,
                                 smooth_shade=False, color=MESH_COLORS.get(name))
        new_names.append(name + " right")
    if left:
        for name, (verts, tris) in left.items():
            left_verts = verts.copy()
            left_verts[:, 0] = 2.0 * mirror_x - verts[:, 0]
            # mirroring inverts the face orientation, so flip the winding back
            left_tris = np.ascontiguousarray(tris[:, ::-1])
            ps.register_surface_mesh(name + " left", left_verts, left_tris,
                                     smooth_shade=False, color=MESH_COLORS.get(name))
            new_names.append(name + " left")

    for name in mesh_names:
        if name not in new_names and ps.has_surface_mesh(name):
            ps.remove_surface_mesh(name)
    mesh_names = new_names

    # scene bounds, used to aim the camera
    lo = np.min([v.min(axis=0) for v, t in right.values()], axis=0)
    hi = np.max([v.max(axis=0) for v, t in right.values()], axis=0)
    if left:
        l_lo = np.min([v.min(axis=0) for v, t in left.values()], axis=0)
        l_hi = np.max([v.max(axis=0) for v, t in left.values()], axis=0)
        lo = np.minimum(lo, [2.0 * mirror_x - l_hi[0], l_lo[1], l_lo[2]])
        hi = np.maximum(hi, [2.0 * mirror_x - l_lo[0], l_hi[1], l_hi[2]])
    scene_lo, scene_hi = lo, hi

    last_build_ms = (time.perf_counter() - t0) * 1000


def export_stl():
    global status_line
    written = []

    right = dactylmesh.build_manifolds(Dact(make_config(half_params["right"])))
    verts, tris = dactylmesh.mesh_arrays(right)
    filename = path.join("things", "right_gui.stl")
    dactylmesh.write_stl(filename, verts, tris)
    written.append(filename)

    left = dactylmesh.build_manifolds(Dact(make_config(left_source())))
    verts, tris = dactylmesh.mesh_arrays(left)
    verts = verts.copy()
    verts[:, 0] = -verts[:, 0]
    tris = np.ascontiguousarray(np.asarray(tris)[:, ::-1])
    filename = path.join("things", "left_gui.stl")
    dactylmesh.write_stl(filename, verts, tris)
    written.append(filename)

    status_line = "Wrote " + " and ".join(written)
    print(status_line)


def export_step():
    global status_line
    import cadquery as cq
    print("Building STEP with the CadQuery pipeline, this takes a while...")
    t0 = time.perf_counter()
    written = []
    try:
        for side, p in (("right", half_params["right"]), ("left", left_source())):
            conf = make_config(p)
            conf.show_caps = False  # caps are display-only
            model = Dact(conf).model_right_debug()
            if side == "left":
                model = model.mirror('YZ')
            filename = path.join("things", side + "_gui.step")
            cq.exporters.export(w=model, fname=filename, exportType="STEP")
            written.append(filename)
        status_line = "Wrote %s in %.1f s" % (" and ".join(written), time.perf_counter() - t0)
    except Exception as e:
        status_line = "STEP export failed: %s" % e
    print(status_line)


def slider3(label, values, v_min, v_max):
    changed_any = False
    for i, axis in enumerate(("x", "y", "z")):
        changed, values[i] = psim.SliderFloat("%s %s" % (label, axis), values[i], v_min, v_max)
        changed_any = changed_any or changed
    return changed_any


def draw_half_controls(p, tag):
    # tag makes the ImGui widget ids unique per half (text after ## is not shown)
    s = "##" + tag
    changed_any = False

    for label, key, mn, mx in (
        ("Rows", "nrows", 4, MAX_ROWS),
        ("Columns", "ncols", 5, 9),
        ("Center column", "centercol", 2, 4),
    ):
        changed, p[key] = psim.SliderInt(label + s, p[key], mn, mx)
        changed_any = changed_any or changed

    for label, key, mn, mx in (
        ("Column curvature (deg)", "alpha_deg", 3.0, 30.0),
        ("Row curvature (deg)", "beta_deg", 1.0, 15.0),
        ("Tenting angle (deg)", "tenting_deg", 0.0, 40.0),
        ("Height offset (mm)", "keyboard_z_offset", 0.0, 30.0),
        ("Plate thickness (mm)", "plate_thickness", 0.6, 3.0),
        ("Web thickness (mm)", "web_thickness", 2.0, 6.0),
        ("Keycap space (mm)", "keycap_space", 17.0, 22.0),
        ("Wall thickness (mm)", "wall_thickness", 1.0, 5.0),
        ("Wall outward flare (mm)", "wall_flare", 0.0, 15.0),
    ):
        changed, p[key] = psim.SliderFloat(label + s, p[key], mn, mx)
        changed_any = changed_any or changed

    changed, p["use_wide_pinky"] = psim.Checkbox("Wide pinky keys" + s, p["use_wide_pinky"])
    changed_any = changed_any or changed

    if p["use_wide_pinky"]:
        changed, p["pinky_uniform"] = psim.Checkbox("Same pinky width for all rows" + s, p["pinky_uniform"])
        changed_any = changed_any or changed
        if p["pinky_uniform"]:
            changed, p["pinky_width"] = psim.SliderFloat("Pinky key width (mm)" + s, p["pinky_width"], 19.0, 34.0)
            if changed:
                # keep the per row widths in sync so switching to per row
                # editing starts from the uniform value
                p["pinky_rows"] = [p["pinky_width"]] * MAX_ROWS
            changed_any = changed_any or changed
        else:
            for i in range(int(p["nrows"]) - 1):
                changed, p["pinky_rows"][i] = psim.SliderFloat(
                    "Pinky width row %d (mm)%s" % (i, s), p["pinky_rows"][i], 19.0, 34.0)
                changed_any = changed_any or changed

    if psim.TreeNode("Thumb keys" + s):
        changed_any = slider3("TR rotation" + s, p["tr_rot"], -60.0, 60.0) or changed_any
        changed_any = slider3("TR location" + s, p["tr_loc"], -60.0, 30.0) or changed_any
        changed_any = slider3("TL rotation" + s, p["tl_rot"], -60.0, 60.0) or changed_any
        changed_any = slider3("TL location" + s, p["tl_loc"], -60.0, 30.0) or changed_any
        psim.TreePop()

    return changed_any


def ui():
    global status_line
    changed_any = False

    psim.TextUnformatted("Rebuild time: %.0f ms" % last_build_ms)
    psim.Separator()

    changed, view["mirror"] = psim.Checkbox("Mirror halves (one set of sliders)", view["mirror"])
    if changed and not view["mirror"]:
        # start independent editing from the current shared values
        half_params["left"] = copy.deepcopy(half_params["right"])
    changed_any = changed_any or changed

    for label, key in (
        ("Show left half", "show_left"),
        ("Show keycaps", "show_caps"),
        ("Show walls", "show_walls"),
    ):
        changed, view[key] = psim.Checkbox(label, view[key])
        changed_any = changed_any or changed

    changed, view["half_gap"] = psim.SliderFloat("Gap between halves (mm)", view["half_gap"], 0.0, 200.0)
    changed_any = changed_any or changed

    psim.Separator()
    if view["mirror"]:
        changed_any = draw_half_controls(half_params["right"], "both") or changed_any
    else:
        psim.TextUnformatted("Right half")
        changed_any = draw_half_controls(half_params["right"], "right") or changed_any
        psim.Separator()
        psim.TextUnformatted("Left half")
        changed_any = draw_half_controls(half_params["left"], "left") or changed_any

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
