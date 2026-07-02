# Fast mesh pipeline for the dactyl generator.
#
# Builds the same geometry as the CadQuery pipeline but with manifold3d (the
# Manifold engine, also used by OpenSCAD's fast backend). Mesh booleans and
# convex hulls take milliseconds instead of the seconds that OCCT B-rep
# booleans need, which is what makes the live preview GUI possible.
#
# The key positions come from the exact same Dact point functions
# (key_frame_point_sets, connector_point_sets, wall_outline_points,
# get_key_xyz), so both pipelines always generate the same layout. The
# CadQuery pipeline remains the source of truth for STEP export.

import numpy as np
from manifold3d import Manifold, OpType


def hull(points):
    return Manifold.hull_points(np.asarray(points, dtype=np.float64))


def mesh_arrays(manifold):
    # returns (vertices float32 (n,3), triangles int (m,3)) for a viewer
    m = manifold.to_mesh()
    return np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts)


def _box_pts(x0, x1, y0, y1, z0, z1):
    return [(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)]


class MeshPipeline:
    """Builds keyboard component meshes from a Dact instance."""

    def __init__(self, dact):
        self.d = dact
        self.c = dact.config

    # ---- placement helpers (numpy versions of the cq place functions) ----

    def _thumb_transform(self, which):
        # matches thumb_XX_place: rotate about global x, then y, then z axes,
        # then translate to thumb origin plus the per key location offset
        th = self.c.thumb_keys
        rx, ry, rz = np.radians(getattr(th, which + "_rot"))
        Rx = np.array([[1, 0, 0],
                       [0, np.cos(rx), -np.sin(rx)],
                       [0, np.sin(rx), np.cos(rx)]])
        Ry = np.array([[np.cos(ry), 0, np.sin(ry)],
                       [0, 1, 0],
                       [-np.sin(ry), 0, np.cos(ry)]])
        Rz = np.array([[np.cos(rz), -np.sin(rz), 0],
                       [np.sin(rz), np.cos(rz), 0],
                       [0, 0, 1]])
        R = Rz @ Ry @ Rx
        t = np.asarray(self.d.thumb_origin, dtype=float) + np.asarray(getattr(th, which + "_loc"), dtype=float)
        return R, t

    def thumb_pts(self, which, local_pts):
        R, t = self._thumb_transform(which)
        return np.asarray(local_pts, dtype=float) @ R.T + t

    def key_pts(self, col, row, local_pts, x_sh=0.0, y_sh=0.0, z_sh=0.0):
        return np.array([self.d.get_key_xyz(col, row, list(p), x_sh, y_sh, z_sh) for p in local_pts])

    # ---- components ----

    def key_frames(self):
        solids = []
        for pts_frame, pts_hole in self.d.key_frame_point_sets():
            solids.append(hull(pts_frame) - hull(pts_hole))
        return solids

    def connectors(self):
        return [hull(places) for places in self.d.connector_point_sets()]

    def thumb(self):
        # thumb plates: single_plate((a,a,a,a)) plus the double_plate
        # extensions, built as hulls of their corner points (see thumb() and
        # double_plate() in dactylutils)
        c = self.c
        ks = c.keycap_space
        hole_w = c.keyswitch_hole_width
        hole_h = c.keyswitch_hole_height
        pt = c.plate_thickness
        wt = c.web_thickness
        mw = c.mount_width
        mh = c.mount_height
        ph = (c.thumb_plate_length - ks) / 2  # double_plate plate_height

        plate_outer = _box_pts(-ks / 2, ks / 2, -ks / 2, ks / 2, 0, pt)
        # the hole overshoots the plate in z slightly so the subtraction
        # leaves no coplanar face slivers
        plate_hole = _box_pts(-hole_w / 2, hole_w / 2, -hole_h / 2, hole_h / 2, -0.05, pt + 0.05)
        top_ext = _box_pts(-mw / 2, mw / 2, mh / 2, mh / 2 + ph, pt - wt, pt)
        bot_ext = _box_pts(-mw / 2, mw / 2, -mh / 2 - ph, -mh / 2, pt - wt, pt)

        solids = []
        for which in ("tr", "tl"):  # the thumb_count == 2 layout
            solids.append(hull(self.thumb_pts(which, plate_outer)) - hull(self.thumb_pts(which, plate_hole)))
            solids.append(hull(self.thumb_pts(which, top_ext)))
            solids.append(hull(self.thumb_pts(which, bot_ext)))
        return solids

    def thumb_connectors(self):
        # Mesh version of thumb_connectors() for thumb_count >= 2. Every web
        # post is represented by its top and bottom point; each window of 3
        # posts from the triangle_hulls chains becomes one convex hull.
        c = self.c
        d = self.d
        pt = c.plate_thickness
        wt = c.web_thickness
        mw, mh = c.mount_width, c.mount_height
        z_top, z_bot = pt, pt - wt
        thick = c.switch_plate_wall_thickness

        def thumb_post(which, sx, sy):
            # matches thumb_post_tr/tl/bl/br: sx and sy pick the corner sign
            x = sx * mw / 2
            y = sy * mh / 1.15
            return self.thumb_pts(which, [(x, y, z_top), (x, y, z_bot)])

        def key_post(col, row, corner):
            # matches web_post_tl/tr/bl/br including the special widths on
            # columns 2 and 3 and the wide pinky column
            wide = c.use_wide_pinky and col == c.ncols - 1
            if corner in ("tr", "br"):
                x = mw / 2 + ((self.d.pinky_space(row) - c.keycap_space) if wide else 0)
            else:
                x = -(mw / 2)
                if col == 2:
                    x = -(c.keycap_space + 2 * wt) / 2
                elif col == 3:
                    x = -(c.keycap_space + wt) / 2
            y = mh / 2 if corner in ("tl", "tr") else -(mh / 2)
            return np.array([d.get_key_xyz(col, row, [x, y, z]) for z in (z_top, z_bot)])

        def key_post_g(col, row, x_sh, y_sh, z_sh):
            # matches web_post_br_g: a thin bar along x at the bottom right
            # frame corner (the "skinny wall" fix post)
            xc = mw / 2 + pt - wt / 2
            y = -(mh / 2)
            return np.array([
                d.get_key_xyz(col, row, [xc + s * thick / 2, y, 0.0], x_sh, y_sh, z_sh)
                for s in (-1, 1)
            ])

        x_sh_col1 = 0.7 - (0.5 * thick)
        y_sh = 0.3
        z_sh = pt
        cr = d.cornerrow

        chains = [
            # connector between the two thumb key hole frames
            [
                thumb_post("tl", +1, +1),  # tl place, post tr
                thumb_post("tl", +1, -1),  # tl place, post br
                thumb_post("tr", -1, +1),  # tr place, post tl
                thumb_post("tr", -1, -1),  # tr place, post bl
            ],
            # top two thumb keys to the main keyboard, left to right
            [
                thumb_post("tl", -1, +1),  # tl place, post tl
                key_post(0, cr, "bl"),
                thumb_post("tl", +1, +1),  # tl place, post tr
                key_post(0, cr, "br"),
                thumb_post("tr", -1, +1),  # tr place, post tl
                key_post(1, cr, "bl"),
                thumb_post("tr", +1, +1),  # tr place, post tr
                key_post_g(1, cr, x_sh_col1, y_sh, z_sh),
            ],
        ]

        solids = []
        for chain in chains:
            for i in range(len(chain) - 2):
                solids.append(hull(np.concatenate(chain[i:i + 3])))
        return solids

    def walls(self):
        # Mesh version of walls_test using the same offset rings. Instead of
        # one closed tube, the wall is built as a union of one convex hull per
        # outline edge (the "ribbon" between all rings along that edge).
        # Adjacent ribbons share their corner cross sections, so the union is
        # watertight, and local self intersections of the offset polygon at
        # concave corners are simply absorbed by the union instead of
        # producing a broken tube.
        outline = np.asarray(self.d.wall_outline_points(), dtype=float)
        solids = []
        for spec in self.d.wall_loft_specs():
            rings = np.stack([
                self.d.mitre_offset(outline, off) + np.array([0.0, 0.0, dz])
                for off, dz in spec
            ])  # shape (rings, outline points, 3)
            n = rings.shape[1]
            for j in range(n):
                j1 = (j + 1) % n
                solids.append(hull(np.concatenate([rings[:, j, :], rings[:, j1, :]])))
        return solids

    def caps(self):
        # display-only keycaps, matching sa_cap: a hull of a bottom, middle
        # and top rectangle
        c = self.c
        mh = c.mount_height

        def cap_pts(sa_length):
            bw2 = sa_length / 2
            bl2 = mh / 2
            pw2, pl2 = bw2 - 3, bl2 - 3
            pts = _box_pts(-bw2, bw2, -bl2, bl2, 0.05, 0.15)
            pts += _box_pts(-pw2, pw2, -pl2, pl2, 12.0, 12.1)
            if bw2 == bl2:
                m = sa_length / 2
                pts += _box_pts(-m, m, -m, m, 6.0, 6.1)
            lift = np.array([0.0, 0.0, 5 + c.plate_thickness])
            return np.asarray(pts, dtype=float) + lift

        cap = cap_pts(c.mount_width)
        thumb_cap = cap @ np.array([[0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0]]).T  # rotated 90 degrees

        def pinky_cap(row):
            # 1 mm narrower than the key clearance width, centered on the
            # widened key (which extends to the right of the mount area)
            sa_length = self.d.pinky_space(row) - 1.0
            return cap_pts(sa_length) + np.array([(sa_length - c.mount_width) / 2, 0.0, 0.0])

        solids = []
        for column in range(c.ncols):
            for row in range(self.d.lastrow):
                if c.use_wide_pinky and column == c.ncols - 1:
                    local = pinky_cap(row)
                else:
                    local = cap
                solids.append(hull(self.key_pts(column, row, local)))

        for which in ("tr", "tl"):
            solids.append(hull(self.thumb_pts(which, thumb_cap)))
        return solids


def build_keyboard(dact, show_caps=True, show_walls=True, trim_z=0.0):
    """Builds the full keyboard preview. Returns {name: (vertices, triangles)}.

    The body and walls are unioned and trimmed at z=trim_z, mirroring the
    block cut in model_right_debug. Caps are display-only and not unioned.
    """
    pipe = MeshPipeline(dact)

    # key_frames must run first: it fills dact.key_pt, which walls() needs
    solids = pipe.key_frames()
    solids += pipe.connectors()
    solids += pipe.thumb()
    solids += pipe.thumb_connectors()
    body = Manifold.batch_boolean(solids, OpType.Add).trim_by_plane((0, 0, 1), trim_z)

    out = {"body": mesh_arrays(body)}
    if show_walls:
        walls = Manifold.batch_boolean(pipe.walls(), OpType.Add).trim_by_plane((0, 0, 1), trim_z)
        out["walls"] = mesh_arrays(walls)
    if show_caps:
        out["caps"] = mesh_arrays(Manifold.compose(pipe.caps()))
    return out


def build_manifolds(dact, show_walls=True, trim_z=0.0):
    """Like build_keyboard but returns one fused Manifold (for STL export)."""
    pipe = MeshPipeline(dact)
    solids = pipe.key_frames()
    solids += pipe.connectors()
    solids += pipe.thumb()
    solids += pipe.thumb_connectors()
    if show_walls:
        solids += pipe.walls()
    return Manifold.batch_boolean(solids, OpType.Add).trim_by_plane((0, 0, 1), trim_z)


def write_stl(filename, verts, tris):
    """Writes a binary STL file from vertex and triangle arrays."""
    tri_pts = np.asarray(verts, dtype=np.float64)[np.asarray(tris)]
    normals = np.cross(tri_pts[:, 1] - tri_pts[:, 0], tri_pts[:, 2] - tri_pts[:, 0])
    lengths = np.linalg.norm(normals, axis=1, keepdims=True)
    lengths[lengths == 0] = 1.0
    normals = normals / lengths

    n = len(tri_pts)
    record = np.zeros(n, dtype=[("normal", "<f4", 3), ("verts", "<f4", (3, 3)), ("attr", "<u2")])
    record["normal"] = normals
    record["verts"] = tri_pts
    with open(filename, "wb") as f:
        f.write(b"dactyl mesh export".ljust(80, b" "))
        f.write(np.uint32(n).tobytes())
        f.write(record.tobytes())
