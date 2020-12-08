import cadquery as cq
from dataclasses import dataclass
import numpy as np
import os
import os.path as path
from numpy import pi
import os.path as path
from scipy.spatial import ConvexHull as sphull
import traceback
import sys

class Tester:

    @dataclass(init=True)
    class Config:
        test : int = 1
        kak : bool = False

class CalcUtils:
    @staticmethod
    def deg2rad(degrees: float) -> float:
        return degrees * pi / 180

    @staticmethod
    def rad2deg(rad: float) -> float:
        return rad * 180 / pi

class Dact:

    @dataclass(init = True) # Dataclass (struct) with constructor to set config values.
    class Config:
        # ######################
        # ## Shape parameters ##
        # ######################
        show_caps : bool    = True
        nrows : int         = 5  # key rows
        ncols : int         = 6  # key columns
        #column_style        ='fixed' # options include :standard, :orthographic, and :fixed. Moved to constructor
        alpha : float       = pi / 12.0  # curvature of the columns
        beta : float        = pi / 36.0  # curvature of the rows
        centerrow : int     = nrows - 3  # controls front_back tilt
        centercol : int     = 3  # controls left_right tilt / tenting (higher number is more tenting)
        tenting_angle : float = pi / 12.0  # or, change this for more precise tenting control
        thumb_offsets = [6, -3, 7]
        keyboard_z_offset = (
            9  # controls overall height# original=9 with centercol=3# use 16 for centercol=2
        )

        extra_width = 2.5  # extra space between the base of keys# original= 2
        extra_height = 1.0  # original= 0.5

        wall_z_offset = -15  # length of the first downward_sloping part of the wall (negative)
        wall_xy_offset = 5  # offset in the x and/or y direction for the first downward_sloping part of the wall (negative)
        wall_thickness = 2  # wall thickness parameter# originally 5
        left_wall_x_offset = 10
        left_wall_z_offset = 3
        ## Settings for column_style == :fixed
        ## The defaults roughly match Maltron settings
        ##   http://patentimages.storage.googleapis.com/EP0219944A2/imgf0002.png
        ## fixed_z overrides the z portion of the column ofsets above.
        ## NOTE: THIS DOESN'T WORK QUITE LIKE I'D HOPED.
        fixed_angles = [CalcUtils.deg2rad(10), CalcUtils.deg2rad(10), 0, 0, 0, CalcUtils.deg2rad(-15), CalcUtils.deg2rad(-15)]
        fixed_x = [-41.5, -22.5, 0, 20.3, 41.4, 65.5, 89.6]  # relative to the middle finger
        fixed_z = [12.1, 8.3, 0, 5, 10.7, 14.5, 17.5]
        fixed_tenting = CalcUtils.deg2rad(0)
        #######################
        ## General variables ##
        #######################
        lastrow = nrows - 1
        cornerrow = lastrow - 1
        lastcol = ncols - 1

        ####################
        ## Web Connectors ##
        ####################
        web_thickness = 3.5 + .5
        post_size = 0.1
        post_adj = post_size / 2
        #################
        ## Switch Hole ##
        #################

        keyswitch_height = 14.4  ## Was 14.1, then 14.25
        keyswitch_width = 14.4

        sa_profile_key_height = 12.7

        plate_thickness = 4
        mount_width = keyswitch_width + 3
        mount_height = keyswitch_height + 3
        mount_thickness = plate_thickness

        SWITCH_WIDTH = 14
        SWITCH_HEIGHT = 14
        CLIP_THICKNESS = 1.4
        CLIP_UNDERCUT = 1.0
        UNDERCUT_TRANSITION = .2
        # ######################
        # ## USB holder geometry ##
        # ######################
        usb_holder_size = [6.5, 10.0, 13.6]
        usb_holder_thickness = 4
        ###################
        # ##Teensy geometry ##
        ###################
        teensy_width = 20
        teensy_height = 12
        teensy_length = 33
        teensy2_length = 53
        teensy_pcb_thickness = 2
        teensy_holder_width = 7 + teensy_pcb_thickness
        teensy_holder_height = 6 + teensy_width
        teensy_offset_height = 5
        teensy_holder_top_length = 18
        ###################
        # ##Screw insert geometry ##
        ###################
        screw_insert_height = 3.8
        screw_insert_bottom_radius = 5.31 / 2
        screw_insert_top_radius = 5.1 / 2
        ###################
        # ## Wire post geometry ##
        ###################
        wire_post_height = 7
        wire_post_overhang = 3.5
        wire_post_diameter = 2.6

        # ######################
        # ## Script parameters ##
        # ######################
        script_verbose_func : bool = False
        script_print_shapes : bool = False

    def __init__(self, config: Config):
        self.config = config

        ## Settings for column_style == :fixed
        ## The defaults roughly match Maltron settings
        ##   http://patentimages.storage.googleapis.com/EP0219944A2/imgf0002.png
        ## fixed_z overrides the z portion of the column offsets (see config dataclass)
        ## NOTE: THIS DOESN'T WORK QUITE LIKE I'D HOPED.
        self.column_style = "fixed"
        if self.config.nrows > 5:
            self.column_style = "orthographic"
        else:
            self.column_style = "standard"  # options include :standard, :orthographic, and :fixed

        self.cap_top_height = self.config.plate_thickness + self.config.sa_profile_key_height
        self.row_radius = ((self.config.mount_height + self.config.extra_height) / 2) / (
            np.sin(self.config.alpha / 2)) + self.cap_top_height
        self.column_radius = (
                                     ((self.config.mount_width + self.config.extra_width) / 2) / (np.sin(self.config.beta / 2))
                             ) + self.cap_top_height
        self.column_x_delta = -1 - self.column_radius * np.sin(self.config.beta)
        self.column_base_angle = self.config.beta * (self.config.centercol - 2)
        # body of the Dact constructor
        self.rj9_position = self.rj9_position()
        self.usb_holder_position = self.key_position(
            list(np.array(self.wall_locate2(0, 1)) + np.array([0, (self.config.mount_height / 2), 0])), 1, 0
        )
        self.teensy_top_xy = self.key_position(self.wall_locate3(-1, 0), 0, self.config.centerrow - 1)
        self.teensy_bot_xy = self.key_position(self.wall_locate3(-1, 0), 0, self.config.centerrow + 1)
        self.teensy_holder_length = self.teensy_top_xy[1] - self.teensy_bot_xy[1]
        self.teensy_holder_offset = -self.teensy_holder_length / 2
        self.teensy_holder_top_offset = (self.config.teensy_holder_top_length / 2) - self.teensy_holder_length

        # screw inserts:
        self.screw_insert_holes = self.screw_insert_all_shapes(
            self.config.screw_insert_bottom_radius, self.config.screw_insert_top_radius, self.config.screw_insert_height
        )
        self.screw_insert_outers = self.screw_insert_all_shapes(
            self.config.screw_insert_bottom_radius + 1.6,
            self.config.screw_insert_top_radius + 1.6,
            self.config.screw_insert_height + 1.5,
        )
        self.screw_insert_screw_holes = self.screw_insert_all_shapes(1.7, 1.7, 350)

        self.script_shape_debug_counter = 0

    def print_fu(self, *args):
        if self.config.script_verbose_func:
            print(*args)

    # Prints the shape. For example to debug model building steps in the script.
    def print_model(self, shape, s = ""):
        if self.config.script_print_shapes:
            self.script_shape_debug_counter = self.script_shape_debug_counter + 1
            filename = "debug_"+ str(self.script_shape_debug_counter) +" "+ s +".step"
            full_path = path.join("things", filename)
            cq.exporters.export(w=shape, fname=full_path, exportType='STEP')
            print(os.open(full_path, os.O_RDONLY))

    # Constructor to generate the keyboard for the left hand
    #@classmethod

    # Constructor to generate the keyboard for the right hand
    #@classmethod

    #def generate_keyboard(self):
    #    if self.config.nrows > 5:
    #        self.config.column_style = "orthographic"
    #    else:
    #        self.config.column_style = "standard"  # options include :standard, :orthographic, and :fixed

    def rotate(self, shape, angle):
        self.print_fu('rotate()')
        origin = (0, 0, 0)
        shape = shape.rotate(axisStartPoint=origin, axisEndPoint=(1, 0, 0), angleDegrees=angle[0])
        shape = shape.rotate(axisStartPoint=origin, axisEndPoint=(0, 1, 0), angleDegrees=angle[1])
        shape = shape.rotate(axisStartPoint=origin, axisEndPoint=(0, 0, 1), angleDegrees=angle[2])
        return shape

    def translate(self, shape, vector):
        self.print_fu('translate()')
        return shape.translate(tuple(vector))

    def mirror(self, shape, plane=None):
        self.print_fu('mirror()')
        return shape.mirror(mirrorPlane=plane)

    def union(self, shapes):
        self.print_fu('union()')
        shape = None
        for item in shapes:
            if shape is None:
                shape = item
            else:
                shape = shape.union(item)
        return shape

    def face_from_points(self, points):
        self.print_fu('face_from_points()')
        edges = []
        num_pnts = len(points)
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % num_pnts]
            edges.append(
                cq.Edge.makeLine(
                    cq.Vector(p1[0], p1[1], p1[2]),
                    cq.Vector(p2[0], p2[1], p2[2]),
                )
            )

        face = cq.Face.makeFromWires(cq.Wire.assembleEdges(edges))

        return face

    def hull_from_points(self, points):
        self.print_fu('hull_from_points()')
        hull_calc = sphull(points)
        n_faces = len(hull_calc.simplices)

        faces = []
        for i in range(n_faces):
            face_items = hull_calc.simplices[i]
            fpnts = []
            for item in face_items:
                fpnts.append(points[item])
            faces.append(self.face_from_points(fpnts))

        shape = cq.Solid.makeSolid(cq.Shell.makeShell(faces))
        shape = cq.Workplane('XY').union(shape)
        return shape

    def hull_from_shapes(self, shapes, points=None):
        self.print_fu('hull_from_shapes()')
        vertices = []
        for shape in shapes:
            verts = shape.vertices()
            for vert in verts.objects:
                vertices.append(np.array(vert.toTuple()))
        if points is not None:
            for point in points:
                vertices.append(np.array(point))

        shape = self.hull_from_points(vertices)
        return shape

    def tess_hull(self, shapes, sl_tol=.5, sl_angTol=1):
        self.print_fu('hull_from_shapes()')
        vertices = []
        solids = []
        for wp in shapes:
            for item in wp.solids().objects:
                solids.append(item)

        for shape in solids:
            verts = shape.tessellate(sl_tol, sl_angTol)[0]
            for vert in verts:
                vertices.append(np.array(vert.toTuple()))

        shape = self.hull_from_points(vertices)
        return shape

    def column_offset(self, column: int) -> list:
        self.print_fu('column_offset()')
        if column == 2:
            return [0, 2.82, -4.5]
        elif column >= 4:
            return [0, -12, 5.64]  # original [0 -5.8 5.64]
        else:
            return [0, 0, 0]

    def single_plate(self, cylinder_segments=100):
        top_wall = cq.Workplane("XY").box(self.config.keyswitch_width + 3, 1.5, self.config.plate_thickness)
        top_wall = top_wall.translate((0, (1.5 / 2) + (self.config.keyswitch_height / 2), self.config.plate_thickness / 2))

        left_wall = cq.Workplane("XY").box(1.5, self.config.keyswitch_height + 3, self.config.plate_thickness)
        left_wall = left_wall.translate(((1.5 / 2) + (self.config.keyswitch_width / 2), 0, self.config.plate_thickness / 2))

        side_nub = cq.Workplane("XY").union(cq.Solid.makeCylinder(radius=1, height=2.75))
        side_nub = side_nub.translate((0, 0, -2.75 / 2.0))
        side_nub = self.rotate(side_nub, (90, 0, 0))
        side_nub = side_nub.translate((self.config.keyswitch_width / 2, 0, 1))
        nub_cube = cq.Workplane("XY").box(1.5, 2.75, self.config.plate_thickness)
        nub_cube = nub_cube.translate(((1.5 / 2) + (self.config.keyswitch_width / 2), 0, self.config.plate_thickness / 2))

        side_nub2 = self.tess_hull(shapes=(side_nub, nub_cube))
        side_nub2 = side_nub2.union(side_nub).union(nub_cube)

        plate_half1 = top_wall.union(left_wall).union(side_nub2)
        plate_half2 = plate_half1
        plate_half2 = self.mirror(plate_half2, 'XZ')
        plate_half2 = self.mirror(plate_half2, 'YZ')

        plate = plate_half1.union(plate_half2)

        return plate

    ################
    ## SA Keycaps ##
    ################

    sa_length = 18.25
    sa_double_length = 37.5

    def sa_cap(self, Usize=1):
        # MODIFIED TO NOT HAVE THE ROTATION.  NEEDS ROTATION DURING ASSEMBLY
        sa_length = 18.25

        bw2 = Usize * sa_length / 2
        bl2 = sa_length / 2
        m = 0
        pw2 = 6 * Usize + 1
        pl2 = 6

        if Usize == 1:
            m = 17 / 2

        k1 = cq.Workplane('XY').polyline([(bw2, bl2), (bw2, -bl2), (-bw2, -bl2), (-bw2, bl2), (bw2, bl2)])
        k1 = cq.Wire.assembleEdges(k1.edges().objects)
        k1 = cq.Workplane('XY').add(cq.Solid.extrudeLinear(outerWire=k1, innerWires=[], vecNormal=cq.Vector(0, 0, 0.1)))
        k1 = k1.translate((0, 0, 0.05))
        k2 = cq.Workplane('XY').polyline([(pw2, pl2), (pw2, -pl2), (-pw2, -pl2), (-pw2, pl2), (pw2, pl2)])
        k2 = cq.Wire.assembleEdges(k2.edges().objects)
        k2 = cq.Workplane('XY').add(cq.Solid.extrudeLinear(outerWire=k2, innerWires=[], vecNormal=cq.Vector(0, 0, 0.1)))
        k2 = k2.translate((0, 0, 12.0))
        if m > 0:
            m1 = cq.Workplane('XY').polyline([(m, m), (m, -m), (-m, -m), (-m, m), (m, m)])
            m1 = cq.Wire.assembleEdges(m1.edges().objects)
            m1 = cq.Workplane('XY').add(
                cq.Solid.extrudeLinear(outerWire=m1, innerWires=[], vecNormal=cq.Vector(0, 0, 0.1)))
            m1 = m1.translate((0, 0, 6.0))
            key_cap = self.hull_from_shapes((k1, k2, m1))
        else:
            key_cap = self.hull_from_shapes((k1, k2))

        key_cap = key_cap.translate((0, 0, 5 + self.config.plate_thickness))
        # key_cap = key_cap.color((220 / 255, 163 / 255, 163 / 255, 1))

        return key_cap

    #########################
    ## Placement Functions ##
    #########################

    def rotate_around_x(self, position, angle):
        # print_fu('rotate_around_x()')
        t_matrix = np.array(
            [
                [1, 0, 0],
                [0, np.cos(angle), -np.sin(angle)],
                [0, np.sin(angle), np.cos(angle)],
            ]
        )
        return np.matmul(t_matrix, position)

    def rotate_around_y(self, position, angle):
        self.print_fu('rotate_around_y()')
        t_matrix = np.array(
            [
                [np.cos(angle), 0, np.sin(angle)],
                [0, 1, 0],
                [-np.sin(angle), 0, np.cos(angle)],
            ]
        )
        return np.matmul(t_matrix, position)

    def apply_key_geometry(self,
            shape,
            translate_fn,
            rotate_x_fn,
            rotate_y_fn,
            column,
            row,
            #column_style = "fixed", # optional argument. Already defined in config / constructor
    ):
        self.print_fu('apply_key_geometry()' + " column style = " + self.column_style)

        column_angle = self.config.beta * (self.config.centercol - column)

        if self.column_style == "orthographic":
            column_z_delta = self.column_radius * (1 - np.cos(column_angle))
            shape = translate_fn(shape, [0, 0, -self.row_radius])
            shape = rotate_x_fn(shape, self.alpha * (self.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius])
            shape = rotate_y_fn(shape, column_angle)
            shape = translate_fn(
                shape, [-(column - self.centercol) * self.column_x_delta, 0, self.column_z_delta]
            )
            shape = translate_fn(shape, self.column_offset(column))

        elif self.column_style == "fixed":
            shape = rotate_y_fn(shape, self.config.fixed_angles[column])
            shape = translate_fn(shape, [self.config.fixed_x[column], 0, self.config.fixed_z[column]])
            shape = translate_fn(shape, [0, 0, -(self.row_radius + self.config.fixed_z[column])])
            shape = rotate_x_fn(shape, self.config.alpha * (self.config.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius + self.config.fixed_z[column]])
            shape = rotate_y_fn(shape, self.config.fixed_tenting)
            shape = translate_fn(shape, [0,self.column_offset(column)[1], 0])

        else:
            shape = translate_fn(shape, [0, 0, -self.row_radius])
            shape = rotate_x_fn(shape, self.config.alpha * (self.config.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius])
            shape = translate_fn(shape, [0, 0, -self.column_radius])
            shape = rotate_y_fn(shape, column_angle)
            shape = translate_fn(shape, [0, 0, self.column_radius])
            shape = translate_fn(shape,self. column_offset(column))

        shape = rotate_y_fn(shape, self.config.tenting_angle)
        shape = translate_fn(shape, [0, 0, self.config.keyboard_z_offset])

        return shape

    def x_rot(self, shape, angle):
        # print_fu('x_rot()')
        return self.rotate(shape, [CalcUtils.rad2deg(angle), 0, 0])

    def y_rot(self, shape, angle):
        # print_fu('y_rot()')
        return self.rotate(shape, [0, CalcUtils.rad2deg(angle), 0])

    def key_place(self, shape, column, row):
        self.print_fu('key_place()')
        return self.apply_key_geometry(shape, self.translate, self.x_rot, self.y_rot, column, row)

    def add_translate(self, shape, xyz):
        self.print_fu('add_translate()')
        vals = []
        for i in range(len(shape)):
            vals.append(shape[i] + xyz[i])
        return vals

    def key_position(self, position, column, row):
        self.print_fu('key_position()')
        return self.apply_key_geometry(
            position, self.add_translate, self.rotate_around_x, self.rotate_around_y, column, row
        )

    def key_holes(self):
        self.print_fu('key_holes()')
        # hole = single_plate()
        holes = []
        for column in range(self.config.ncols):
            for row in range(self.config.nrows):
                if (column in [2, 3]) or (not row == self.config.lastrow):
                    holes.append(self.key_place(self.single_plate(), column, row))

        shape = self.union(holes)

        return shape

    def caps(self):
        caps = None
        for column in range(self.config.ncols):
            for row in range(self.config.nrows):
                if (column in [2, 3]) or (not row == self.config.lastrow):
                    if caps is None:
                        caps = self.key_place(self.sa_cap(), column, row)
                    else:
                        caps = caps.add(self.key_place(self.sa_cap(), column, row))

        return caps

    def web_post(self):
        self.print_fu('web_post()')
        post = cq.Workplane("XY").box(self.config.post_size, self.config.post_size, self.config.web_thickness)
        post = post.translate((0, 0, self.config.plate_thickness - (self.config.web_thickness / 2)))
        return post

    def web_post_tr(self):
        # self.print_fu('web_post_tr()')
        return self.web_post().translate(((self.config.mount_width / 2) - self.config.post_adj, (self.config.mount_height / 2) - self.config.post_adj, 0))

    def web_post_tl(self):
        # self.print_fu('web_post_tl()')
        return self.web_post().translate((-(self.config.mount_width / 2) + self.config.post_adj, (self.config.mount_height / 2) - self.config.post_adj, 0))

    def web_post_bl(self):
        # self.print_fu('web_post_bl()')
        return self.web_post().translate((-(self.config.mount_width / 2) + self.config.post_adj, -(self.config.mount_height / 2) + self.config.post_adj, 0))

    def web_post_br(self):
        # self.print_fu('web_post_br()')
        return self.web_post().translate(((self.config.mount_width / 2) - self.config.post_adj, -(self.config.mount_height / 2) + self.config.post_adj, 0))

    def triangle_hulls(self, shapes):
        self.print_fu('triangle_hulls()')
        hulls = [cq.Workplane('XY')]
        for i in range(len(shapes) - 2):
            hulls.append(self.hull_from_shapes(shapes[i: (i + 3)]))

        return self.union(hulls)

    def connectors(self):
        self.print_fu('connectors()')
        hulls = []
        for column in range(self.config.ncols - 1):
            for row in range(self.config.lastrow):  # need to consider last_row?
                # for row in range(nrows):  # need to consider last_row?
                places = []
                places.append(self.key_place(self.web_post_tl(), column + 1, row))
                places.append(self.key_place(self.web_post_tr(), column, row))
                places.append(self.key_place(self.web_post_bl(), column + 1, row))
                places.append(self.key_place(self.web_post_br(), column, row))
                hulls.append(self.triangle_hulls(places))

        for column in range(self.config.ncols):
            # for row in range(nrows-1):
            for row in range(self.config.cornerrow):
                places = []
                places.append(self.key_place(self.web_post_bl(), column, row))
                places.append(self.key_place(self.web_post_br(), column, row))
                places.append(self.key_place(self.web_post_tl(), column, row + 1))
                places.append(self.key_place(self.web_post_tr(), column, row + 1))
                hulls.append(self.triangle_hulls(places))

        for column in range(self.config.ncols - 1):
            # for row in range(nrows-1):  # need to consider last_row?
            for row in range(self.config.cornerrow):  # need to consider last_row?
                places = []
                places.append(self.key_place(self.web_post_br(), column, row))
                places.append(self.key_place(self.web_post_tr(), column, row + 1))
                places.append(self.key_place(self.web_post_bl(), column + 1, row))
                places.append(self.key_place(self.web_post_tl(), column + 1, row + 1))
                hulls.append(self.triangle_hulls(places))

        return self.union(hulls)

    ############
    ## Thumbs ##
    ############

    def thumborigin(self):
        # self.print_fu('thumborigin()')
        origin = self.key_position([ self.config.mount_width / 2, -(self.config.mount_height / 2), 0], 1, self.config.cornerrow)
        for i in range(len(origin)):
            origin[i] = origin[i] + self.config.thumb_offsets[i]
        return origin

    def thumb_tr_place(self, shape):
        self.print_fu('thumb_tr_place()')
        shape = self.rotate(shape, [10, -23, 10])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-12, -16, 3])
        return shape

    def thumb_tl_place(self, shape):
        self.print_fu('thumb_tl_place()')
        shape = self.rotate(shape, [10, -23, 10])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-32, -15, -2])
        return shape

    def thumb_mr_place(self, shape):
        self.print_fu('thumb_mr_place()')
        shape = self.rotate(shape, [-6, -34, 48])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-29, -40, -13])
        return shape

    def thumb_ml_place(self, shape):
        self.print_fu('thumb_ml_place()')
        shape = self.rotate(shape, [6, -34, 40])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-51, -25, -12])
        return shape

    def thumb_br_place(self, shape):
        self.print_fu('thumb_br_place()')
        shape = self.rotate(shape, [-16, -33, 54])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-37.8, -55.3, -25.3])
        return shape

    def thumb_bl_place(self, shape):
        self.print_fu('thumb_bl_place()')
        shape = self.rotate(shape, [-4, -35, 52])
        shape = shape.translate(self.thumborigin())
        shape = shape.translate([-56.3, -43.3, -23.5])
        return shape

    def thumb_1x_layout(self, shape, cap=False):
        self.print_fu('thumb_1x_layout()')
        if cap:
            shapes = self.thumb_mr_place(shape)
            shapes = shapes.add(self.thumb_ml_place(shape))
            shapes = shapes.add(self.thumb_br_place(shape))
            shapes = shapes.add(self.thumb_bl_place(shape))
        else:
            shapes = self.union(
                [
                    self.thumb_mr_place(shape),
                    self.thumb_ml_place(shape),
                    self.thumb_br_place(shape),
                    self.thumb_bl_place(shape),
                ]
            )
        return shapes

    def thumb_15x_layout(self, shape, cap=False):
        self.print_fu('thumb_15x_layout()')
        if cap:
            shape = self.rotate(shape, (0, 0, 90))
            return self.thumb_tr_place(shape).add(self.thumb_tl_place(shape).solids().objects[0])
        else:
            return self.thumb_tr_place(shape).union(self.thumb_tl_place(shape))

    def double_plate(self):
        self.print_fu('double_plate()')
        plate_height = (self.sa_double_length - self.config.mount_height) / 3
        # plate_height = (2*sa_length-self.config.mount_height) / 3
        top_plate = cq.Workplane("XY").box( self.config.mount_width, plate_height, self.config.web_thickness)
        top_plate = self.translate(top_plate,
                              [0, (plate_height + self.config.mount_height) / 2, self.config.plate_thickness - (self.config.web_thickness / 2)]
                              )
        return self.union((top_plate, self.mirror(top_plate, 'XZ')))

    def thumbcaps(self):
        t1 = self.thumb_1x_layout(self.sa_cap(1), cap=True)
        # t15 = thumb_15x_layout(self.rotate(sa_cap(1.5), [0, 0, pi / 2]), cap=True)
        t15 = self.thumb_15x_layout(self.sa_cap(1.5), cap=True)
        return t1.add(t15)

    def thumb(self):
        self.print_fu('thumb()')
        shape = self.thumb_1x_layout(self.single_plate())
        shape = shape.union(self.thumb_15x_layout(self.single_plate()))
        shape = shape.union(self.thumb_15x_layout(self.double_plate()))
        return shape

    def thumb_post_tr(self):
        self.print_fu('thumb_post_tr()')
        return self.translate(self.web_post(),
                         [( self.config.mount_width / 2) - self.config.post_adj, (self.config.mount_height / 1.15) - self.config.post_adj, 0]
                         )

    def thumb_post_tl(self):
        self.print_fu('thumb_post_tl()')
        return self.translate(self.web_post(),
                         [-( self.config.mount_width / 2) + self.config.post_adj, (self.config.mount_height / 1.15) - self.config.post_adj, 0]
                         )

    def thumb_post_bl(self):
        self.print_fu('thumb_post_bl()')
        return self.translate(self.web_post(),
                         [-( self.config.mount_width / 2) + self.config.post_adj, -(self.config.mount_height / 1.15) + self.config.post_adj, 0]
                         )

    def thumb_post_br(self):
        self.print_fu('thumb_post_br()')
        return self.translate(self.web_post(),
                         [( self.config.mount_width / 2) - self.config.post_adj, -(self.config.mount_height / 1.15) + self.config.post_adj, 0]
                         )

    def thumb_connectors(self):
        self.print_fu('thumb_connectors()')
        hulls = []

        # Top two
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_tl_place(self.thumb_post_tr()),
                    self.thumb_tl_place(self.thumb_post_br()),
                    self.thumb_tr_place(self.thumb_post_tl()),
                    self.thumb_tr_place(self.thumb_post_bl()),
                ]
            )
        )

        # bottom two on the right
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_br_place(self.web_post_tr()),
                    self.thumb_br_place(self.web_post_br()),
                    self.thumb_mr_place(self.web_post_tl()),
                    self.thumb_mr_place(self.web_post_bl()),
                ]
            )
        )

        # bottom two on the left
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_br_place(self.web_post_tr()),
                    self.thumb_br_place(self.web_post_br()),
                    self.thumb_mr_place(self.web_post_tl()),
                    self.thumb_mr_place(self.web_post_bl()),
                ]
            )
        )
        # centers of the bottom four
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_bl_place(self.web_post_tr()),
                    self.thumb_bl_place(self.web_post_br()),
                    self.thumb_ml_place(self.web_post_tl()),
                    self.thumb_ml_place(self.web_post_bl()),
                ]
            )
        )

        # top two to the middle two, starting on the left
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_br_place(self.web_post_tl()),
                    self.thumb_bl_place(self.web_post_bl()),
                    self.thumb_br_place(self.web_post_tr()),
                    self.thumb_bl_place(self.web_post_br()),
                    self.thumb_mr_place(self.web_post_tl()),
                    self.thumb_ml_place(self.web_post_bl()),
                    self.thumb_mr_place(self.web_post_tr()),
                    self.thumb_ml_place(self.web_post_br()),
                ]
            )
        )

        # top two to the main keyboard, starting on the left
        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_tl_place(self.thumb_post_tl()),
                    self.thumb_ml_place(self.web_post_tr()),
                    self.thumb_tl_place(self.thumb_post_bl()),
                    self.thumb_ml_place(self.web_post_br()),
                    self.thumb_tl_place(self.thumb_post_br()),
                    self.thumb_mr_place(self.web_post_tr()),
                    self.thumb_tr_place(self.thumb_post_bl()),
                    self.thumb_mr_place(self.web_post_br()),
                    self.thumb_tr_place(self.thumb_post_br()),
                ]
            )
        )

        hulls.append(
            self.triangle_hulls(
                [
                    self.thumb_tl_place(self.thumb_post_tl()),
                    self.key_place(self.web_post_bl(), 0, self.config.cornerrow),
                    self.thumb_tl_place(self.thumb_post_tr()),
                    self.key_place(self.web_post_br(), 0, self.config.cornerrow),
                    self.thumb_tr_place(self.thumb_post_tl()),
                    self.key_place(self.web_post_bl(), 1, self.config.cornerrow),
                    self.thumb_tr_place(self.thumb_post_tr()),
                    self.key_place(self.web_post_br(), 1, self.config.cornerrow),
                    self.key_place(self.web_post_tl(), 2, self.config.lastrow),
                    self.key_place(self.web_post_bl(), 2, self.config.lastrow),
                    self.thumb_tr_place(self.thumb_post_tr()),
                    self.key_place(self.web_post_bl(), 2, self.config.lastrow),
                    self.thumb_tr_place(self.thumb_post_br()),
                    self.key_place(self.web_post_br(), 2, self.config.lastrow),
                    self.key_place(self.web_post_bl(), 3, self.config.lastrow),
                    self.key_place(self.web_post_tr(), 2, self.config.lastrow),
                    self.key_place(self.web_post_tl(), 3, self.config.lastrow),
                    self.key_place(self.web_post_bl(), 3, self.config.cornerrow),
                    self.key_place(self.web_post_tr(), 3, self.config.lastrow),
                    self.key_place(self.web_post_br(), 3, self.config.cornerrow),
                    self.key_place(self.web_post_bl(), 4, self.config.cornerrow),
                ]
            )
        )

        hulls.append(
            self.triangle_hulls(
                [
                    self.key_place(self.web_post_br(), 1, self.config.cornerrow),
                    self.key_place(self.web_post_tl(), 2, self.config.lastrow),
                    self.key_place(self.web_post_bl(), 2, self.config.cornerrow),
                    self.key_place(self.web_post_tr(), 2, self.config.lastrow),
                    self.key_place(self.web_post_br(), 2, self.config.cornerrow),
                    self.key_place(self.web_post_bl(), 3, self.config.cornerrow),
                ]
            )
        )

        hulls.append(
            self.triangle_hulls(
                [
                    self.key_place(self.web_post_tr(), 3, self.config.lastrow),
                    self.key_place(self.web_post_br(), 3, self.config.lastrow),
                    self.key_place(self.web_post_tr(), 3, self.config.lastrow),
                    self.key_place(self.web_post_bl(), 4, self.config.cornerrow),
                ]
            )
        )

        return self.union(hulls)

    ##########
    ## Case ##
    ##########

    def bottom_hull(self, p, height=0.001):
        self.print_fu("bottom_hull()")
        shape = None
        for item in p:
            # proj = sl.projection()(p)
            # t_shape = sl.linear_extrude(height=height, twist=0, convexity=0, center=True)(
            #      proj
            # )
            vertices = []
            verts = item.faces('<Z').vertices()
            for vert in verts.objects:
                v0 = vert.toTuple()
                v1 = [v0[0], v0[1], -10]
                vertices.append(np.array(v0))
                vertices.append(np.array(v1))

            t_shape = self.hull_from_points(vertices)

            # t_shape = self.translate(t_shape, [0, 0, height / 2 - 10])

            if shape is None:
                shape = t_shape

            for shp in (*p, shape, t_shape):
                try:
                    shp.vertices()
                except:
                    0
            # shape = shape.union(hull_from_shapes((item, shape, t_shape)))
            shape = shape.union(self.hull_from_shapes((shape, t_shape)))
            # shape = shape.self.union(t_shape)

        return shape

    def left_key_position(self, row, direction):
        self.print_fu("left_key_position()")
        pos = np.array(
            self.key_position([-self.config.mount_width * 0.5, direction * self.config.mount_height * 0.5, 0], 0, row)
        )
        return list(pos - np.array([self.config.left_wall_x_offset, 0, self.config.left_wall_z_offset]))

    def left_key_place(self, shape, row, direction):
        self.print_fu("left_key_place()")
        pos = self.left_key_position(row, direction)
        return shape.translate(pos)

    def wall_locate1(self, dx, dy):
        self.print_fu("wall_locate1()")
        return [dx * self.config.wall_thickness, dy * self.config.wall_thickness, -1]

    def wall_locate2(self, dx, dy):
        self.print_fu("wall_locate2()")
        return [dx * self.config.wall_xy_offset, dy * self.config.wall_xy_offset, self.config.wall_z_offset]

    def wall_locate3(self, dx, dy):
        self.print_fu("wall_locate3()")
        return [
            dx * (self.config.wall_xy_offset + self.config.wall_thickness),
            dy * (self.config.wall_xy_offset + self.config.wall_thickness),
            self.config.wall_z_offset,
        ]

    def wall_brace(self, place1, dx1, dy1, post1, place2, dx2, dy2, post2):
        self.print_fu("wall_brace()")
        hulls = []

        hulls.append(place1(post1))
        hulls.append(place1(self.translate(post1, self.wall_locate1(dx1, dy1))))
        hulls.append(place1(self.translate(post1, self.wall_locate2(dx1, dy1))))
        hulls.append(place1(self.translate(post1, self.wall_locate3(dx1, dy1))))

        hulls.append(place2(post2))
        hulls.append(place2(self.translate(post2, self.wall_locate1(dx2, dy2))))
        hulls.append(place2(self.translate(post2, self.wall_locate2(dx2, dy2))))
        hulls.append(place2(self.translate(post2, self.wall_locate3(dx2, dy2))))
        shape1 = self.hull_from_shapes(hulls)

        hulls = []
        hulls.append(place1(self.translate(post1, self.wall_locate2(dx1, dy1))))
        hulls.append(place1(self.translate(post1, self.wall_locate3(dx1, dy1))))
        hulls.append(place2(self.translate(post2, self.wall_locate2(dx2, dy2))))
        hulls.append(place2(self.translate(post2, self.wall_locate3(dx2, dy2))))
        shape2 = self.bottom_hull(hulls)

        return shape1.union(shape2)
        # return shape1

    def key_wall_brace(self, x1, y1, dx1, dy1, post1, x2, y2, dx2, dy2, post2):
        self.print_fu("key_wall_brace()")
        return self.wall_brace(
            (lambda shape: self.key_place(shape, x1, y1)),
            dx1,
            dy1,
            post1,
            (lambda shape: self.key_place(shape, x2, y2)),
            dx2,
            dy2,
            post2,
        )

    def back_wall(self):
        self.print_fu("back_wall()")
        x = 0
        shape = cq.Workplane('XY')
        shape = shape.union(self.key_wall_brace(x, 0, 0, 1, self.web_post_tl(), x, 0, 0, 1, self.web_post_tr()))
        for i in range(self.config.ncols - 1):
            x = i + 1
            shape = shape.union(self.key_wall_brace(x, 0, 0, 1, self.web_post_tl(), x, 0, 0, 1, self.web_post_tr()))
            shape = shape.union(self.key_wall_brace(
                x, 0, 0, 1, self.web_post_tl(), x - 1, 0, 0, 1, self.web_post_tr()
            ))
        shape = shape.union(self.key_wall_brace(
            self.config.lastcol, 0, 0, 1, self.web_post_tr(), self.config.lastcol, 0, 1, 0, self.web_post_tr()
        ))
        return shape

    def right_wall(self):
        self.print_fu("right_wall()")
        y = 0
        shape = cq.Workplane('XY')
        shape = shape.union(
            self.key_wall_brace(
                self.config.lastcol, y, 1, 0, self.web_post_tr(), self.config.lastcol, y, 1, 0, self.web_post_br()
            )
        )
        for i in range(self.config.lastrow - 1):
            y = i + 1
            shape = shape.union(self.key_wall_brace(
                self.config.lastcol, y, 1, 0, self.web_post_tr(), self.config.lastcol, y, 1, 0, self.web_post_br()
            ))
            shape = shape.union(self.key_wall_brace(
                self.config.lastcol, y, 1, 0, self.web_post_br(), self.config.lastcol, y - 1, 1, 0, self.web_post_tr()
            ))
        shape = shape.union(self.key_wall_brace(
            self.config.lastcol,
            self.config.cornerrow,
            0,
            -1,
            self.web_post_br(),
            self.config.lastcol,
            self.config.cornerrow,
            1,
            0,
            self.web_post_br(),
        ))
        return shape

    def left_wall(self):
        self.print_fu('left_wall()')
        shape = cq.Workplane('XY')
        shape = shape.union(self.wall_brace(
            (lambda sh: self.key_place(sh, 0, 0)),
            0,
            1,
            self.web_post_tl(),
            (lambda sh: self.left_key_place(sh, 0, 1)),
            0,
            1,
            self.web_post(),
        ))

        shape = shape.union(self.wall_brace(
            (lambda sh: self.left_key_place(sh, 0, 1)),
            0,
            1,
            self.web_post(),
            (lambda sh: self.left_key_place(sh, 0, 1)),
            -1,
            0,
            self.web_post(),
        ))

        for i in range(self.config.lastrow):
            y = i
            temp_shape1 = self.wall_brace(
                (lambda sh: self.left_key_place(sh, y, 1)),
                -1,
                0,
                self.web_post(),
                (lambda sh: self.left_key_place(sh, y, -1)),
                -1,
                0,
                self.web_post(),
            )
            temp_shape2 = self.hull_from_shapes((
                self.key_place(self.web_post_tl(), 0, y),
                self.key_place(self.web_post_bl(), 0, y),
                self.left_key_place(self.web_post(), y, 1),
                self.left_key_place(self.web_post(), y, -1),
            ))
            shape = shape.union(temp_shape1)
            shape = shape.union(temp_shape2)

        for i in range(self.config.lastrow - 1):
            y = i + 1
            temp_shape1 = self.wall_brace(
                (lambda sh: self.left_key_place(sh, y - 1, -1)),
                -1,
                0,
                self.web_post(),
                (lambda sh: self.left_key_place(sh, y, 1)),
                -1,
                0,
                self.web_post(),
            )
            temp_shape2 = self.hull_from_shapes((
                self.key_place(self.web_post_tl(), 0, y),
                self.key_place(self.web_post_bl(), 0, y - 1),
                self.left_key_place(self.web_post(), y, 1),
                self.left_key_place(self.web_post(), y - 1, -1),
            ))
            shape = shape.union(temp_shape1)
            shape = shape.union(temp_shape2)

        return shape

    def front_wall(self):
        self.print_fu('front_wall()')
        shape = cq.Workplane('XY')
        shape = shape.union(
            self.key_wall_brace(
                self.config.lastcol, 0, 0, 1, self.web_post_tr(), self.config.lastcol, 0, 1, 0, self.web_post_tr()
            )
        )
        shape = shape.union(self.key_wall_brace(
            3, self.config.lastrow, 0, -1, self.web_post_bl(), 3, self.config.lastrow, 0.5, -1, self.web_post_br()
        ))
        shape = shape.union(self.key_wall_brace(
            3, self.config.lastrow, 0.5, -1, self.web_post_br(), 4, self.config.cornerrow, 1, -1, self.web_post_bl()
        ))
        for i in range(self.config.ncols - 4):
            x = i + 4
            shape = shape.union(self.key_wall_brace(
                x, self.config.cornerrow, 0, -1, self.web_post_bl(), x, self.config.cornerrow, 0, -1, self.web_post_br()
            ))
        for i in range(self.config.ncols - 5):
            x = i + 5
            shape = shape.union(self.key_wall_brace(
                x, self.config.cornerrow, 0, -1, self.web_post_bl(), x - 1, self.config.cornerrow, 0, -1, self.web_post_br()
            ))

        return shape

    def thumb_walls(self):
        self.print_fu('thumb_walls()')
        # thumb, walls
        shape = cq.Workplane('XY')
        shape = shape.union(
            self.wall_brace(
                self.thumb_mr_place, 0, -1, self.web_post_br(), self.thumb_tr_place, 0, -1, self.thumb_post_br()
            )
        )
        shape = shape.union(self.wall_brace(
            self.thumb_mr_place, 0, -1, self.web_post_br(), self.thumb_mr_place, 0, -1, self.web_post_bl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_br_place, 0, -1, self.web_post_br(), self.thumb_br_place, 0, -1, self.web_post_bl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_ml_place, -0.3, 1, self.web_post_tr(), self.thumb_ml_place, 0, 1, self.web_post_tl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_bl_place, 0, 1, self.web_post_tr(), self.thumb_bl_place, 0, 1, self.web_post_tl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_br_place, -1, 0, self.web_post_tl(), self.thumb_br_place, -1, 0, self.web_post_bl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_bl_place, -1, 0, self.web_post_tl(), self.thumb_bl_place, -1, 0, self.web_post_bl()
        ))
        # thumb, corners
        shape = shape.union(self.wall_brace(
            self.thumb_br_place, -1, 0, self.web_post_bl(), self.thumb_br_place, 0, -1, self.web_post_bl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_bl_place, -1, 0, self.web_post_tl(), self.thumb_bl_place, 0, 1, self.web_post_tl()
        ))
        # thumb, tweeners
        shape = shape.union(self.wall_brace(
            self.thumb_mr_place, 0, -1, self.web_post_bl(), self.thumb_br_place, 0, -1, self.web_post_br()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_ml_place, 0, 1, self.web_post_tl(), self.thumb_bl_place, 0, 1, self.web_post_tr()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_bl_place, -1, 0, self.web_post_bl(), self.thumb_br_place, -1, 0, self.web_post_tl()
        ))
        shape = shape.union(self.wall_brace(
            self.thumb_tr_place,
            0,
            -1,
            self.thumb_post_br(),
            (lambda sh: self.key_place(sh, 3, self.config.lastrow)),
            0,
            -1,
            self.web_post_bl(),
        ))

        return shape

    def thumb_connection(self):
        self.print_fu('thumb_connection()')
        shape = cq.Workplane('XY')
        # clunky bit on the top left thumb connection  (normal connectors don't work well)
        shape = shape.union(self.bottom_hull(
            [
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.config.cornerrow, -1
                ),
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.config.cornerrow, -1
                ),
                self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate2(-0.3, 1))),
                self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate3(-0.3, 1))),
            ]
        ))

        # shape = shape.union(hull_from_shapes(

        shape = shape.union(
            self.hull_from_shapes(
                [
                    self.left_key_place(
                        self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.config.cornerrow, -1
                    ),
                    self.left_key_place(
                        self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.config.cornerrow, -1
                    ),
                    self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate2(-0.3, 1))),
                    self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate3(-0.3, 1))),
                    self.thumb_tl_place(self.thumb_post_tl()),
                ]
            )
        )  # )

        shape = shape.union(self.hull_from_shapes(
            [
                self.left_key_place(self.web_post(), self.config.cornerrow, -1),
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.config.cornerrow, -1
                ),
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.config.cornerrow, -1
                ),
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.config.cornerrow, -1
                ),
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.left_key_place(self.web_post(), self.config.cornerrow, -1),
                self.left_key_place(
                    self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.config.cornerrow, -1
                ),
                self.key_place(self.web_post_bl(), 0, self.config.cornerrow),
                self.key_place(self.translate(self.web_post_bl(), self.wall_locate1(-1, 0)), 0, self.config.cornerrow),
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.thumb_ml_place(self.web_post_tr()),
                self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate1(-0.3, 1))),
                self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate2(-0.3, 1))),
                self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate3(-0.3, 1))),
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))

        return shape

    def case_walls(self):
        self.print_fu('case_walls()')
        shape = cq.Workplane('XY')
        return (
            self.union([
                shape,
                self.back_wall(),
                self.left_wall(),
                self.right_wall(),
                self.front_wall(),
                self.thumb_walls(),
                self.thumb_connection(),
            ])
        )

    # turned this into function
    def rj9_position(self):
        rj9_start = list(
            np.array([0, -3, 0])
            + np.array(
                self.key_position(
                    (list(np.array(self.wall_locate3(0, 1)) + np.array([0, (self.config.mount_height / 2), 0]))),
                    0,
                    0,
                )
            )
        )
        rj9_pos = (rj9_start[0], rj9_start[1], 11)

        return rj9_pos # returns rj9 position

    def rj9_cube(self):
        self.print_fu('rj9_cube()')
        shape = cq.Workplane("XY").box(14.78, 13, 22.38)

        return shape

    def rj9_space(self):
        self.print_fu('rj9_space()')
        return self.rj9_cube().translate(self.rj9_position)

    def rj9_holder(self):
        self.print_fu('rj9_holder()')
        shape = cq.Workplane("XY").box(10.78, 9, 18.38).translate((0, 2, 0))
        shape = shape.union(cq.Workplane("XY").box(10.78, 13, 5).translate((0, 0, 5)))
        shape = self.rj9_cube().cut(shape)
        shape = shape.translate(self.rj9_position)

        return shape

    def usb_holder(self):
        self.print_fu('usb_holder()')
        shape = cq.Workplane("XY").box(
            self.config.usb_holder_size[0] + self.config.usb_holder_thickness,
            self.config.usb_holder_size[1],
            self.config.usb_holder_size[2] + self.config.usb_holder_thickness,
        )
        shape = shape.translate(
            (
                self.usb_holder_position[0],
                self.usb_holder_position[1],
                (self.config.usb_holder_size[2] + self.config.usb_holder_thickness) / 2,
            )
        )
        return shape

    def usb_holder_hole(self):
        self.print_fu('usb_holder_hole()')
        shape = cq.Workplane("XY").box(*self.config.usb_holder_size)
        shape = shape.translate(
            (
                self.usb_holder_position[0],
                self.usb_holder_position[1],
                (self.config.usb_holder_size[2] + self.config.usb_holder_thickness) / 2,
            )
        )
        return shape

    def teensy_holder(self):
        self.print_fu('teensy_holder()')
        s1 = cq.Workplane("XY").box(3, self.config.teensy_holder_length, 6 + self.config.teensy_width)
        s1 = self.translate(s1, [1.5, self.teensy_holder_offset, 0])

        s2 = cq.Workplane("XY").box(self.config.teensy_pcb_thickness, self.config.teensy_holder_length, 3)
        s2 = self.translate(s2,
                       (
                           (self.config.teensy_pcb_thickness / 2) + 3,
                           self.config.teensy_holder_offset,
                           -1.5 - (self.config.teensy_width / 2),
                       )
                       )

        s3 = cq.Workplane("XY").box(self.config.teensy_pcb_thickness, self.config.teensy_holder_top_length, 3)
        s3 = self.translate(s3,
                       [
                           (self.config.teensy_pcb_thickness / 2) + 3,
                           self.config.teensy_holder_top_offset,
                           1.5 + (self.config.teensy_width / 2),
                       ]
                       )

        s4 = cq.Workplane("XY").box(4, self.config.teensy_holder_top_length, 4)
        s4 = self.translate(s4,
                       [self.config.teensy_pcb_thickness + 5, self.config.teensy_holder_top_offset, 1 + (self.config.teensy_width / 2)]
                       )

        shape = self.union((s1, s2, s3, s4))

        shape = shape.translate([-self.config.teensy_holder_width, 0, 0])
        shape = shape.translate([-1.4, 0, 0])
        shape = self.translate(shape,
                          [self.config.teensy_top_xy[0], self.config.teensy_top_xy[1] - 1, (6 + self.config.teensy_width) / 2]
                          )

        return shape

    def screw_insert_shape(self, bottom_radius, top_radius, height):
        self.print_fu('screw_insert_shape()')
        if bottom_radius == top_radius:
            base = cq.Workplane('XY').union(cq.Solid.makeCylinder(radius=bottom_radius, height=height)).translate(
                (0, 0, -height / 2)
            )
        else:
            base = cq.Workplane('XY').union(
                cq.Solid.makeCone(radius1=bottom_radius, radius2=top_radius, height=height)).translate(
                (0, 0, -height / 2))

        shape = self.union((
            base,
            cq.Workplane('XY').union(cq.Solid.makeSphere(top_radius)).translate((0, 0, (height / 2))),
        ))
        return shape

    def screw_insert(self, column, row, bottom_radius, top_radius, height):
        self.print_fu('screw_insert()')
        shift_right = column == self.config.lastcol
        shift_left = column == 0
        shift_up = (not (shift_right or shift_left)) and (row == 0)
        shift_down = (not (shift_right or shift_left)) and (row >= self.config.lastrow)

        if shift_up:
            position = self.key_position(
                list(np.array(self.wall_locate2(0, 1)) + np.array([0, (self.config.mount_height / 2), 0])),
                column,
                row,
            )
        elif shift_down:
            position = self.key_position(
                list(np.array(self.wall_locate2(0, -1)) - np.array([0, (self.config.mount_height / 2), 0])),
                column,
                row,
            )
        elif shift_left:
            position = list(
                np.array(self.left_key_position(row, 0)) + np.array(self.wall_locate3(-1, 0))
            )
        else:
            position = self.key_position(
                list(np.array(self.wall_locate2(1, 0)) + np.array([(self.config.mount_height / 2), 0, 0])),
                column,
                row,
            )

        shape = self.screw_insert_shape(bottom_radius, top_radius, height)
        shape = shape.translate([position[0], position[1], height / 2])

        return shape

    def screw_insert_all_shapes(self, bottom_radius, top_radius, height):
        self.print_fu('screw_insert_all_shapes()')
        shape = (
            self.screw_insert(0, 0, bottom_radius, top_radius, height),
            self.screw_insert(0, self.config.lastrow, bottom_radius, top_radius, height),
            self.screw_insert(2, self.config.lastrow + 0.3, bottom_radius, top_radius, height),
            self.screw_insert(3, 0, bottom_radius, top_radius, height),
            self.screw_insert(self.config.lastcol, 1, bottom_radius, top_radius, height),
        )

        return shape

    def wire_post(self, direction, offset):
        self.print_fu('wire_post()')
        wire_post_diameter = self.config.wire_post_diameter
        wire_post_height = self.config.wire_post_height
        wire_post_overhang = self.config.wire_post_overhang

        s1 = cq.Workplane("XY").box(
            wire_post_diameter, wire_post_diameter, wire_post_height
        )
        s1 = self.translate(s1, [0, -wire_post_diameter * 0.5 * direction, 0])

        s2 = cq.Workplane("XY").box(
            wire_post_diameter, wire_post_overhang, wire_post_diameter
        )
        s2 = self.translate(s2,
                       [0, -wire_post_overhang * 0.5 * direction, -wire_post_height / 2]
                       )

        shape = self.union((s1, s2))
        shape = shape.translate([0, -offset, (-wire_post_height / 2) + 3])
        shape = self.rotate(shape, [-self.config.alpha / 2, 0, 0])
        shape = shape.translate((3, -self.config.mount_height / 2, 0))

        return shape

    def wire_posts(self):
        self.print_fu('wire_posts()')
        thumb_ml_place = self.thumb_ml_place
        wire_post = self.wire_post
        union = self.union
        key_place = self.key_place

        shape = thumb_ml_place(wire_post(1, 0).translate([-5, 0, -2]))
        shape = shape.union(thumb_ml_place(wire_post(-1, 6).translate([0, 0, -2.5])))
        shape = shape.union(thumb_ml_place(wire_post(1, 0).translate([5, 0, -2])))

        for column in range(self.config.lastcol):
            for row in range(self.config.lastrow - 1):
                shape = union([
                    shape,
                    key_place(wire_post(1, 0).translate([-5, 0, 0]), column, row),
                    key_place(wire_post(-1, 6).translate([0, 0, 0]), column, row),
                    key_place(wire_post(1, 0).translate([5, 0, 0]), column, row),
                ])
        return shape

    def model_right(self):
        self.print_fu("model_right()")
        # Generate the square little frames that the key switches fit into.
        shape = cq.Workplane('XY').union(self.key_holes())
        self.print_model(shape, "key_holes")
        # Connect the key switch frames together with extra material
        # This generates the top surface of the keyboard.
        shape = shape.union(self.connectors())
        self.print_model(shape, "connectors")
        ## Generate the thumb switch frames
        shape = shape.union(self.thumb())
        self.print_model(shape, "thumb_switches")
        ## Generate the material between the thumb switch frames and the top surface
        shape = shape.union(self.thumb_connectors())
        self.print_model(shape, "thumb_conn")

        # Generate the vertical outer walls.
        s2 = cq.Workplane('XY').union(self.case_walls())
        self.print_model(s2, "walls")
        # Generate screw insert cilinders (without hole)
        s2 = self.union([s2, *self.screw_insert_outers])
        self.print_model(s2, "screw_insert_cil")
        
        # TODO: add switch for Teensy or USB holder setting?
        # s2 = s2.union(self.teensy_holder())
        s2 = s2.union(self.usb_holder())

        self.print_model(s2, "usb holder")
        # Connector holes
        s2 = s2.cut(self.rj9_space())
        self.print_model(s2, "s2 cut out rj9 space")
        s2 = s2.cut(self.usb_holder_hole())
        self.print_model(s2, "s2 cut out usb space")
        # Create holes in the screw insert cilinders
        s2 = s2.cut(self.union(self.screw_insert_holes))
        self.print_model(s2, "s2 cut out screw holes")
        # Add rj9 holder to shape
        #shape = shape.union(self.rj9_holder()) # georges fix
        s2 = s2.union(self.rj9_holder())
        self.print_model(s2, "add rj9 holder to shape")

        # Add s2 to shape
        #shape = shape.union(s2, tol=.01)
        try:
            shape = shape.union(s2, tol=.01)
            self.print_model(shape, "add s2 to shape")
        except Exception:
            traceback.print_exc()
            sys.exit()

        # TODO: add switch for wire posts setting?
        # shape = shape.union(wire_posts())

        # Create a box shape that is substraced from the model to
        # cut the keyboard along the XY plane (the box is substracted from model)
        block = cq.Workplane("XY").box(350, 350, 40)
        block = block.translate((0, 0, -20))
        shape = shape.cut(block)

        if self.config.show_caps:
            shape = shape.add(self.thumbcaps())
            shape = shape.add(self.caps())

        return shape

    #mod_r = model_right()

    def model_left(self, mod_r):
        model_left = mod_r.mirror('YZ')
        return model_left

    # mod_l = model_left()

    # result = mod_r

    #cq.exporters.export(w=mod_r, fname=path.join("things", r"right_og_py.step"), exportType='STEP')

    # cq.exporters.export(w=mod_r.mirror('YZ'), fname=path.join(r"..", "things", r"left_og_py.step"), exportType='STEP')

    # generates a model for the baseplate
    # sinks model into the XY plane and then creates
    # a countour.
    def baseplate(self, model):
        # shape = mod_r
        shape = model
        shape = shape.translate((0, 0, -0.1))

        square = cq.Workplane('XY').rect(1000, 1000)
        for wire in square.wires().objects:
            plane = cq.Workplane('XY').add(cq.Face.makeFromWires(wire))

        shape = shape.intersect(plane)

        return shape
