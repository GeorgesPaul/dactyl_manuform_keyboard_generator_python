import cadquery as cq
#from cadquery.cadquery import cq
from dataclasses import dataclass, field
import numpy as np
import os
import os.path as path
from numpy import pi
import os.path as path
from scipy.spatial import ConvexHull as sphull
import traceback
import sys
from typing import *
import numba
from array import array
from pyquaternion import Quaternion
import timeit

#temp import for testing different code speeds:
# import timeit
# start_time = timeit.default_timer()
# #code
# elapsed = timeit.default_timer() - start_time
# print("normaal: " + str(elapsed))

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

class Dact(object):

    @dataclass(init = True) # Dataclass (struct) with constructor to set config values.
    class Config:

        @dataclass(init=True)
        class ThumbKeys:  # holds all locations (loc) and angles (rot) for thumb keys

            tr_rot: List[float] = field(default_factory=lambda: [10, -23, 10]           )  # default: [10, -23, 10]
            tr_loc: List[float] = field(default_factory=lambda: [-12, -16, 3]           )  # default: [-12, -16, 3]
            tl_rot: List[float] = field(default_factory=lambda: [10, -23, 10]           )  # default: [10, -23, 10]
            tl_loc: List[float] = field(default_factory=lambda: [-32, -15, -2]          )  # default: [-32, -15, -2]
            mr_rot: List[float] = field(default_factory=lambda: [-6, -34, 48]           )  # default: [-6, -34, 48]
            mr_loc: List[float] = field(default_factory=lambda: [-29, -40, -13]         )  # default: [-29, -40, -13]
            ml_rot: List[float] = field(default_factory=lambda: [6, -34, 40]            )  # default: [6, -34, 40]
            ml_loc: List[float] = field(default_factory=lambda: [-51, -25, -12]         )  # default: [-51, -25, -12]
            br_rot: List[float] = field(default_factory=lambda: [-16, -33, 54]          )  # default: [-16, -33, 54]
            br_loc: List[float] = field(default_factory=lambda: [-37.8, -55.3, -25.3]   )  # default: [-37.8, -55.3, -25.3]
            bl_rot: List[float] = field(default_factory=lambda: [-4, -35, 52]           )  # default: [-4, -35, 52]
            bl_loc: List[float] = field(default_factory=lambda: [-56.3, -43.3, -23.5]   )  # default: [-56.3, -43.3, -23.5]
            # ; it dictates the location of the thumb cluster.
            # ; the first member of the vector is x axis, second one y axis,
            # ; while the last one is y axis.
            # ; the higher x axis value is, the closer it to the pinky.
            # ; the higher y axis value is, the closer it to the alphas.
            # ; the higher z axis value is, the higher it is.
            # (def thumb-offsets [10 -3 -3])
            thumb_offsets : List[float] = field(default_factory=lambda:  [6, -3, 7])

        thumb_keys : ThumbKeys = ThumbKeys()
        # ######################
        # ## Shape parameters ##
        # ######################
        # TODO: make space around bottom of switches wider to allow to fit switch PCBs. Was 17.22mm should be 18.5/19.0 mm or more
        # TODO: fix clojure porting error where Cherry MX switch lips are upside down. Add option to not generate lips?
        # TODO: fix randomly floating thumb switch plane
        # TODO: add keycap stabilizer mountings for wider keys?
		# TODO: implement a front_wall_x_offset and front_wall_z_offset to get some wrist rests (or alternative wrist rest implementation)
        show_caps           : bool  = True
        use_wide_pinky      : bool  = True
        use_inner_column    : bool  = False
        top_rows_extra_key  : bool  = True # TODO: adds an extra key to the far left of the top rows (as seen from right side keyboard)
        side_nubs_enabled   : bool  = False # Enables or disabled the side nubs in the keyswitch plate that hold the (Cherry MX) switches. Not needed in most cases.
        last_row_count      : ""    = "zero" # zero, full or two. TODO: finish implementation based on clojure script
        nrows               : int   = 6  # key rows TODO: fix bug where more than 6 rows causes memory leak. Half-fixed by making style "standard" instead of ortho
        ncols               : int   = 5  # key columns
        thumb_count         : int   = 2  # TODO implement
        #column_style        ='fixed' # options include :standard, :orthographic, and :fixed. Moved to constructor
        alpha               : float = pi / 12.0  # curvature of the columns
        beta                : float = pi / 36.0  # curvature of the rows
        centerrow           : int   = nrows - 3  # controls front_back tilt
        centercol           : int   = 3  # controls left_right tilt / tenting (higher number is more tenting)
        tenting_angle       : float = pi / 12.0  # or, change this for more precise tenting control

        keyboard_z_offset = (
            9  # controls overall height# original=9 with centercol=3# use 16 for centercol=2
        )

        wall_z_offset       : float     = -15  # Depth (downwards) of the first sloped part of the wall from the top of the keyboard.
        wall_xy_offset      : float     = 5  # offset Width (sideways) of the first wall-slope from the top of the keyboard.
        wall_thickness      : float     = 1.5  # wall thickness parameter# originally 5. Lowered a lot to make space for switch PCBs
        left_wall_x_offset  : float     = 10
        left_wall_z_offset  : float     = 3
        ## Settings for column_style == :fixed
        ## The defaults roughly match Maltron settings
        ##   http://patentimages.storage.googleapis.com/EP0219944A2/imgf0002.png
        ## fixed_z overrides the z portion of the column ofsets above.
        ## NOTE: THIS DOESN'T WORK QUITE LIKE I'D HOPED.
        fixed_angles = [CalcUtils.deg2rad(10), CalcUtils.deg2rad(10), 0, 0, 0, CalcUtils.deg2rad(-15), CalcUtils.deg2rad(-15)]

        # original Clojure script values:
        # These values are only used in "fixed" style (not tested)
        # fixed_x = [-41.5, -22.5, 0, 20.3, 41.4, 65.5, 89.6]  # relative to the middle finger
        # fixed_z = [12.1, 8.3, 0, 5, 10.7, 14.5, 17.5]
        fixed_x = [-41.5, -22.5, 0, 20.3, 41.4, 65.5, 89.6]  # relative to the middle finger
        fixed_z = [12.1, 8.3, 0, 5, 10.7, 14.5, 17.5]
        fixed_tenting = CalcUtils.deg2rad(0)

        ####################
        ## Web Connectors ##
        ####################
        web_thickness : float    = 3.5 + .5  # Note: should be higher than plate_thickness and wall_thickness. TODO: add check when value is lower than plate thickness.
        post_size = 0.1
        post_adj = 0#0.3 #post_size / 2
        #################
        ## Switch Hole ##
        #################

        # TODO: refactoring of keyswitch_plate_top/bottom_width, keycap_space, mount_width/height. They all do similar stuff.
        keyswitch_hole_height = 14  ## Note Cherry MX keys are actually 13.9 mm
        keyswitch_hole_width = 14
        keycap_space : float   = 19 # desired total clearance width for key caps (width of keycap base + desired clearance around cap base)
        extra_width: float = 2.1  # extra width between columns in addition to keycap_space
        extra_height: float = 1.0  # original= 0.5 extra space between rows in addition to keycap_space
        switch_plate_wall_thickness : float     = 1.5 #TODO: use as input for functions that are now hardcoded to 1.5
        #keyswitch_plate_top_width = keycap_space # + (2 * switch_plate_wall_thickness) #TODO: validate with keyswitch hole width and key cap width
        #keyswitch_plate_bottom_width = keycap_space #+ (2 * switch_plate_wall_thickness)
        sa_profile_key_height = 12.7
        plate_thickness     :   float   = 1
        mount_width = keycap_space #+ (2 * switch_plate_wall_thickness) # This determines where the column walls start. Higher number = more space between column walls
        mount_height = keycap_space   # This determines spacing between rows
        mount_thickness     :   float   = plate_thickness
        thumb_plate_length = keycap_space + (7 * 2)  # The total length of thumb key frames. Keycap space + (2x 7mm).
        # SWITCH_WIDTH = 14
        # SWITCH_HEIGHT = 14
        # CLIP_THICKNESS = 1.4
        # CLIP_UNDERCUT = 1.0
        # UNDERCUT_TRANSITION = .2
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

        # def __init__(self, th: ThumbKeys):
        #     self.th = th

    def __init__(self, config: Config): #thumb: Config.ThumbKeys

        self.config = config
        #print("tr_loc =" + str(self.config.thumb_keys.tr_loc) + " default: [-15, -16, -1]")

        self.script_shape_debug_counter = 0
        #######################
        ## General variables ##
        #######################
        self.lastrow = config.nrows - 1
        self.cornerrow = self.lastrow - 1
        self.lastcol = config.ncols - 1

        ## Settings for column_style == :fixed
        ## The defaults roughly match Maltron settings
        ##   http://patentimages.storage.googleapis.com/EP0219944A2/imgf0002.png
        ## fixed_z overrides the z portion of the column offsets (see config dataclass)
        ## NOTE: THIS DOESN'T WORK QUITE LIKE I'D HOPED.
        self.column_style = "fixed"
        if self.config.nrows > 5:
            self.column_style = "standard" # "orthographic" TODO: fix quick & dirty hack, because orthographic caused memory leak
        else:
            self.column_style = "standard"  # options include :standard, :orthographic, and :fixed

        self.keyswitch_frame_width = (self.config.keycap_space - self.config.keyswitch_hole_width) / 2

        self.cap_top_height = self.config.plate_thickness + self.config.sa_profile_key_height
        self.row_radius = ((self.config.mount_height + self.config.extra_height) / 2) / (
            np.sin(self.config.alpha / 2)) + self.cap_top_height
        # self.column_radius = (
        #                              ((self.config.mount_width + self.config.extra_width) / 2) / (np.sin(self.config.beta / 2))
        #                      ) + self.cap_top_height
        self.column_radius = (((self.config.keycap_space + self.config.extra_width) / 2) / (
                                 np.sin(self.config.beta / 2))
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
        self.thumb_origin = self.thumborigin()

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

    # This create the (square) frames that will hold the (Cherry MX) switches
    def single_plate(self, keyswitch_frame_width = (2, 2, 2, 2), cylinder_segments=100):

		# Done: replace 1.5 hardcoded by keyswitch_frame_width
        # keyswitch_frame_width holds 4 numbers that correspond to: top, right, bottom, left side of key switch frame
        top, right, bottom, left = keyswitch_frame_width
        plate_thickness = self.config.plate_thickness
        keyhole_w = self.config.keyswitch_hole_width
        keyhole_h = self.config.keyswitch_hole_height

        #starttime = timeit.default_timer()

        # in case of non symmetrical (non square) key frames (to adjust hole and wall locations for columsn 1 2 and 3):
        x_shift = right-left
        y_shift = top-bottom

        # create key plate, shift keyplate (in case it's not symmetrical), create key switch hole, extrude
        key_frame = cq.Workplane("XY").rect(keyhole_w + left + right, keyhole_h + top + bottom).center(-x_shift, -y_shift).rect(keyhole_w, keyhole_h).extrude(-plate_thickness)
        # adjust position of key frame
        key_frame = key_frame.translate((x_shift,y_shift,plate_thickness))
        
        #print("The time difference method 3 is :", timeit.default_timer() - starttime)
        # starttime = timeit.default_timer()
        # print("The time difference method 1 is :", timeit.default_timer() - starttime)

        # TODO: fix code below to work with rewritten (faster) code above
        # TODO: fix: sidenubs are now upside down? Should be flipped.
        if (self.config.side_nubs_enabled):
            side_nub = cq.Workplane("XY").union(cq.Solid.makeCylinder(radius=1, height=2.75))
            side_nub = side_nub.translate((0, 0, -2.75 / 2.0))
            side_nub = self.rotate(side_nub, (90, 0, 0))
            side_nub = side_nub.translate((self.config.keyswitch_hole_width / 2, 0, 1))
            nub_cube = cq.Workplane("XY").box(keyswitch_frame_width, 2.75, self.config.plate_thickness)
            nub_cube = nub_cube.translate(((keyswitch_frame_width / 2) + (self.config.keyswitch_hole_width / 2), 0, self.config.plate_thickness / 2))

            side_nub2 = self.tess_hull(shapes=(side_nub, nub_cube))
            side_nub2 = side_nub2.union(side_nub).union(nub_cube)

            plate_half1 = top_wall.union(right_wall).union(side_nub2)

        return key_frame

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

    # apply geometry for key switch frame connectors
    def apply_key_geometry(self, shape, translate_fn, rotate_x_fn, rotate_y_fn, column, row, x_sh=0, y_sh=0, z_sh=0, rot=(0,0,0)
            #column_style = "fixed", # optional argument. Already defined in config / constructor
    ):
        self.print_fu('apply_key_geometry()' + " column style = " + self.column_style)

        column_angle = self.config.beta * (self.config.centercol - column)

        if self.column_style == "orthographic":
            column_z_delta = self.column_radius * (1 - np.cos(column_angle))
            shape = translate_fn(shape, [0, 0, -self.row_radius])
            shape = rotate_x_fn(shape, self.config.alpha * (self.config.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius])
            shape = rotate_y_fn(shape, column_angle)
            shape = translate_fn(
                shape, [-(column - self.config.centercol) * self.column_x_delta, 0, column_z_delta]
            )
            shape = translate_fn(shape, self.column_offset(column))

        elif self.column_style == "fixed":
            shape = rotate_y_fn(shape, self.config.fixed_angles[column])
            #shape = translate_fn(shape, [self.config.fixed_x[column], 0, self.config.fixed_z[column]])
            shape = translate_fn(shape, [0, 0, -(self.row_radius + self.config.fixed_z[column])])
            shape = rotate_x_fn(shape, self.config.alpha * (self.config.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius + self.config.fixed_z[column]])
            shape = rotate_y_fn(shape, self.config.fixed_tenting)
            shape = translate_fn(shape, [0,self.column_offset(column)[1], 0])

        # these functions create, move and rotate the shape to its column-row location and orientation
        # note the translate and rotate functions are callbacks
        else: #self.column_style == "fixed": # TODO: add x/y/z_sh and rot implementation to above conditions
            shape = translate_fn(shape, [0, 0, -self.row_radius])
            shape = rotate_x_fn(shape, self.config.alpha * (self.config.centerrow - row))
            shape = translate_fn(shape, [0, 0, self.row_radius])
            shape = translate_fn(shape, [0, 0, -self.column_radius])
            shape = rotate_y_fn(shape, column_angle)
            shape = translate_fn(shape, [x_sh, 0+y_sh, self.column_radius+z_sh])
            shape = translate_fn(shape, self.column_offset(column))

        shape = rotate_y_fn(shape, self.config.tenting_angle)
        shape = translate_fn(shape, [0, 0, self.config.keyboard_z_offset])

        return shape

    # Vector addition function. Example: [1,2,3] + [1,1,1] = [2, 3, 4]
    def v_add(self, a, b):
        c = list(map(float.__add__, a, b))
        return c

    # gets a vector [x,y,z] for a point on the keyboard based on [column,row] input
    def get_key_xyz(self, column, row, initial_xyz_offset = [0.0,0.0,0.0], x_sh=0, y_sh=0, z_sh=0):
        column_angle = self.config.beta * (self.config.centercol - column)
        axis_x = [1, 0, 0]
        axis_y = [0, 1, 0]
        axis_z = [0, 0, 1]
        x_sh = float(x_sh)
        y_sh = float(y_sh)
        z_sh = float(z_sh)

        xyz = self.v_add(initial_xyz_offset, [0.0, 0.0, float(-self.row_radius)])
        angle = self.config.alpha * (self.config.centerrow - row)
        if angle != 0.0:
            xyz = Quaternion(axis=axis_x, radians=angle).rotate(np.array(xyz))
        xyz = self.v_add(xyz, [0.0, 0.0, self.row_radius])
        xyz = self.v_add(xyz, [0.0, 0.0, -self.column_radius])
        angle = column_angle
        if angle != 0.0:
            xyz = Quaternion(axis=axis_y, radians=angle).rotate(xyz)
        xyz = self.v_add(xyz, [x_sh, 0.0 + y_sh, self.column_radius + z_sh])
        xyz = self.v_add(xyz, self.column_offset(column))
        angle = self.config.tenting_angle
        #####
        if angle != 0.0:
            xyz = Quaternion(axis=axis_y, radians=angle).rotate(xyz)
        xyz = self.v_add(xyz, [0.0, 0.0, self.config.keyboard_z_offset])

        return xyz

    def get_key_point(self, col, row, key_loc, x_sh=0.0, y_sh=0.0, z_sh=0.0):

        axis_x = [1, 0, 0]
        axis_y = [0, 1, 0]
        axis_z = [0, 0, 1]
        x_key : float = float(self.config.mount_width / 2)
        y_key : float = float(self.config.mount_height / 2)
        z_key : float = float(z_sh)
        xyz: List[float] = []

        if key_loc == "tr":
            pass
        elif key_loc == "br":
            y_key = float(-y_key)
        elif key_loc == "tl":
            x_key = float(-x_key)
        elif key_loc == "bl":
            y_key = float(-y_key)
            x_key = float(-x_key)
        else:
            self.print_debug("Invalid key_loc argument passed to get_key_point_array. Values have to be one of the following strings: tr, br, tl, bl")
            os.exit


        xyz = self.get_key_xyz(col, row, [x_key + x_sh, y_key + y_sh, z_key + z_sh])
        # print(key_loc)
        # print(str(x_key) + " " + str(y_key)+ " " + str(z_key))
        # print(str(xyz))

        return xyz

    def get_thumb_point(self, thumb_key, key_loc, x_sh=0.0, y_sh=0.0, z_sh=0.0):
        axis_x = [1, 0, 0]
        axis_y = [0, 1, 0]
        axis_z = [0, 0, 1]
        x_key: float = float(self.config.mount_width / 2)
        y_key: float = float(self.config.thumb_plate_length / 2)
        z_key: float = float(z_sh)
        xyz : List[float] = []
        loc : List[float] = []
        angle: List[float] = []
        th          = self.config.thumb_keys

        # How a thumb key frame is placed:
        # 1. 3D model points at location 0,0,0 (origin)
        # 2. Rotate thumb frame to desired angle
        # 3. Move to thumb origin
        # 4. Move to final location

        if key_loc == "tr":
            pass
        elif key_loc == "br":
            y_key = float(-y_key)
        elif key_loc == "tl":
            x_key = float(-x_key)
        elif key_loc == "bl":
            y_key = float(-y_key)
            x_key = float(-x_key)
        else:
            self.print_debug("Invalid key_loc argument passed to get_key_point_array. Values have to be one of the following strings: tr, br, tl, bl")
            os.exit

        xyz = [x_key, y_key, z_key]

        if      "tl" in thumb_key:
            loc     = th.tl_loc
            angle   = th.tl_rot
        elif    "tr" in thumb_key:
            loc     = th.tr_loc
            angle   = th.tr_rot
        elif    "ml" in thumb_key:
            loc     = th.ml_loc
            angle   = th.ml_rot
        elif    "mr" in thumb_key:
            loc     = th.mr_loc
            angle   = th.mr_rot
        elif    "bl" in thumb_key:
            loc     = th.bl_loc
            angle   = th.bl_rot
        elif    "br" in thumb_key:
            loc     = th.br_loc
            angle   = th.br_rot
        else:
            self.print_debug("Invalid thumb_key argument passed to get_key_point_array. Values have to be one of the following strings: tr, br, tl, bl")
            os.exit

        xyz = Quaternion(axis=axis_x, degrees=angle[0]).rotate(np.array(xyz))
        xyz = Quaternion(axis=axis_y, degrees=angle[1]).rotate(np.array(xyz))
        xyz = Quaternion(axis=axis_z, degrees=angle[2]).rotate(np.array(xyz))

        xyz = self.v_add(xyz, self.v_add(self.thumb_origin, loc))

        return xyz

    def x_rot(self, shape, angle):
        # print_fu('x_rot()')
        return self.rotate(shape, [CalcUtils.rad2deg(angle), 0, 0])

    def y_rot(self, shape, angle):
        # print_fu('y_rot()')
        return self.rotate(shape, [0, CalcUtils.rad2deg(angle), 0])

    def key_place(self, shape, column, row, x_sh=0, y_sh=0, z_sh=0, rot=(0,0,0)):
        self.print_fu('key_place()')
        # places key related geometry. note that translate, x_rot and y_rot are callback functions
        # x/y/z_sh are shifts on the x/y/z axes

        return self.apply_key_geometry(shape, self.translate, self.x_rot, self.y_rot, column, row, x_sh, y_sh, z_sh, rot)

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

    # builds the frames in which the switches will be placed
    def key_holes(self):
        self.print_fu('key_holes()')
        # hole = single_plate()
        a = self.keyswitch_frame_width
        b = self.keyswitch_frame_width + self.config.switch_plate_wall_thickness
        keyswitch_frame_widths = (a, a, a, a) # standard key switch plane frames are square and symmetrical
        holes = []
        for column in range(self.config.ncols):
            for row in range(self.lastrow):
                #if ((column in [2, 3]) and (not row == self.lastrow)):
                if (column == 2):
                    keyswitch_frame_widths = (a, b, a, b) # make the sides of the 3rd column switch plate wider
                elif (column == 3):
                    keyswitch_frame_widths = (a, b, a, a) # make right sie of the 4th column switch plate wider
                else:
                    keyswitch_frame_widths = (a, a, a, a)

                holes.append(self.key_place(self.single_plate(keyswitch_frame_widths), column, row))
                # Georges add different locations for holes here? or in key_place?

        shape = self.union(holes)

        return shape

    def caps(self):
        caps = None
        if self.config.last_row_count == "zero":
            lastrow = self.lastrow
        else:
            lastrow = self.config.nrows

        for column in range(self.config.ncols):
            for row in range(lastrow): #self.config.nrows
                #if (column in [2, 3]) or (not row == self.lastrow):
                if caps is None:
                    caps = self.key_place(self.sa_cap(), column, row)
                else:
                    caps = caps.add(self.key_place(self.sa_cap(), column, row))

        return caps

    # TODO: add wide pinky function
    # web post functions generate box shapes to work with (Georges)
    def web_post(self, cust_web_thick=0, g_type = False):  #TODO: remove g_type?
        self.print_fu('web_post()')
        plate_thickness = self.config.plate_thickness
        post_size = self.config.post_size
        web_thickness = self.config.web_thickness
        if cust_web_thick == 0:
            post = cq.Workplane("XY").box(post_size, post_size, web_thickness)
        else:
            post = cq.Workplane("XY").box(post_size, post_size, cust_web_thick)

        post = post.translate((0, 0, plate_thickness - (web_thickness / 2))) #plate_thickness - (web_thickness / 2)

        return post

    # tl, tr, bl, br = top left, top right, bottom left, bottom right
    # The perspective is as seen from a bottom view with the keyboard in front of you (as if you're going to type).
    # Example with a key hole frame (bottom view):
    #  TL      TR
    #    +---+
    #    |   |
    #    +---+
    #  BL      BR
    # Note: existing closure scripts also have a view from the bottom.
    # This is against what is convention in electronics design unfortunately. But was kept this way to match Clojure scripts.

    #bl or tl from top
    def web_post_tr(self, col = 0):
        # self.print_fu('web_post_tl()')
        width = self.config.mount_width / 2
        if col == 2:
            width = (self.config.keycap_space + (2 * self.config.web_thickness)) / 2
        elif col == 3:
            width = (self.config.keycap_space + (self.config.web_thickness)) / 2

        shape = self.web_post().translate(((width) - self.config.post_adj,
                                          (self.config.mount_height / 2) - self.config.post_adj,
                                          0))

        return shape

    #tl or bl from top
    def web_post_br(self, col = 0):
        # self.print_fu('web_post_bl()')
        width = self.config.mount_width / 2
        if col == 2:
            width = (self.config.keycap_space + (2 * self.config.web_thickness)) / 2
        elif col == 3:
            width = (self.config.keycap_space + (self.config.web_thickness)) / 2

        shape = self.web_post().translate(((width) - self.config.post_adj,
                                          -(self.config.mount_height / 2) + self.config.post_adj,
                                          0))

        return shape

    # br or tr from top
    def web_post_tl(self, col = 0):
        # self.print_fu('web_post_tr()')
        # post_adj is a tiny number (probably to make geometry overlap a bit on purpose?)
        width = self.config.mount_width / 2
        if col == 2:
            width = (self.config.keycap_space + (2 * self.config.web_thickness)) / 2
        elif col == 3:
            width = (self.config.keycap_space + (self.config.web_thickness)) / 2

        shape = self.web_post().translate((-(width) - self.config.post_adj,
                                          (self.config.mount_height / 2) + self.config.post_adj,
                                          0))

        return shape

    #tr or br from top
    def web_post_bl(self, col = 0):
        # self.print_fu('web_post_br()')
        width = self.config.mount_width / 2
        shift = self.config.post_adj

        if col == 2:
            width = (self.config.keycap_space + (2 * self.config.web_thickness)) / 2
        elif col == 3:
            width = (self.config.keycap_space + (self.config.web_thickness)) / 2

        shape = self.web_post().translate((-(width) - self.config.post_adj,
                                          -(self.config.mount_height / 2) + self.config.post_adj,
                                          0))

        return shape

    # Alternative functions by Georges to avoid "skinny wall" problem when column edges are overlapping instead of side by side
    # was tl
    def web_post_tr_g(self, custom_thick = 1.5, col = 1):
        # self.print_fu('web_post_tl()')
        # adjustment of location of top/bottom connector, when connector thickness is greater then key plate thickness.
        z_adj = 0#self.config.plate_thickness / 2 #self.config.post_adj # moves column walls upwards slightly to merge properly
        bot_adj = self.config.post_adj # adjust the x position of the bottom of the column walls
        top_adj = 0#custom_thick # adjust the top of the wall to fit snugly under the key switch frame
        shape = self.web_post(custom_thick) # get a basic "plank" shape with custom_thick thickness
        shape = self.rotate(shape, (0,90,0)) #rotate the shape (Georges fix, to avoid "skinny walls")

        x = (self.config.mount_width / 2) + top_adj# top_adj makes wider along row
        y = (self.config.mount_height / 2) - self.config.post_adj # post_adj makes wider along column
        if col == 1:
            x = (self.config.mount_width / 2) - bot_adj # make the bottom wall to wall distance wider instead of top

        shape = shape.translate(  ( x,  # - self.config.post_adj # top_adj makes wider along row (x)
                                    y,  # post_adj makes wider along column (y)
                                    z_adj)) # (z)
        return shape

    # was bl
    def web_post_br_g(self, custom_thick = 1.5, col = 1):
        # self.print_fu('web_post_bl()')
        z_adj = 0#self.config.plate_thickness / 2 #self.config.post_adj
        bot_adj = self.config.post_adj  # adjust the x position of the bottom of the column walls
        top_adj = 0#custom_thick  # adjust the top of the wall to fit snugly under the key switch frame
        shape = self.web_post(custom_thick) # get a basic "plank" shape with custom_thick thickness
        shape = self.rotate(shape, (0,90,0)) #rotate the shape (Georges fix, to avoid "skinny walls")

        x = (self.config.mount_width / 2) + top_adj # top_adj makes wider along row
        y = -(self.config.mount_height / 2) + self.config.post_adj # post_adj makes wider along column
        if col == 1:
            x = (self.config.mount_width / 2) - bot_adj

        shape = shape.translate(  ( x, #- self.config.post_adj
                                    y,
                                    z_adj))
        return shape

    # was tr
    def web_post_tl_g(self, custom_thick = 1.5, col = 1):
        # self.print_fu('web_post_tr()')
        z_adj = 0#self.config.plate_thickness / 2 #self.config.post_adj
        bot_adj = self.config.post_adj  # adjust the x position of the bottom of the column walls
        top_adj = 0#custom_thick  # adjust the top of the wall to fit snugly under the key switch frame
        shape = self.web_post(custom_thick)  # get a basic "plank" shape with custom_thick thickness
        shape = self.rotate(shape, (0, 90, 0))  # rotate the shape (Georges fix, to avoid "skinny walls")

        x = -(self.config.mount_width / 2)  + top_adj # top_adj makes wider along row
        y = (self.config.mount_height / 2) - self.config.post_adj # post_adj makes wider along column
        if col == 2: # TODO: remove? seems like top_adj and bot_adj = 0 now and the conditional doesn't add anything. to test.
            x = -(self.config.mount_width / 2) - bot_adj

        shape = shape.translate(  ( x, #- self.config.post_adj
                                    y,
                                    z_adj))

        return shape

    # was br
    def web_post_bl_g(self, custom_thick = 1.5, col = 1):
        # self.print_fu('web_post_br()')
        z_adj = 0#self.config.plate_thickness / 2 #self.config.post_adj
        bot_adj = self.config.post_adj  # adjust the x position of the bottom of the column walls
        top_adj = 0#custom_thick  # adjust the top of the wall to fit snugly under the key switch frame
        shape = self.web_post(custom_thick) # get a basic "plank" shape with custom_thick thickness
        shape = self.rotate(shape, (0,90,0)) #rotate the shape (Georges fix, to avoid "skinny walls")

        x = -(self.config.mount_width / 2)  + top_adj # top_adj makes wider along row
        y = -(self.config.mount_height / 2) + self.config.post_adj # post_adj makes wider along column
        if col == 2:
            x = -(self.config.mount_width / 2) - bot_adj

        shape = shape.translate(  ( x, #- self.config.post_adj
                                    y,
                                    z_adj))

        return shape

    # Creates octangular shape for every 8 geometries in shapes
    def octangle_hulls(self, shapes):
        self.print_fu('octangle_hulls()')
        hulls = [cq.Workplane('XY')]
        count = int((len(shapes) / 8))
        for i in range(count):
            #print(str(i) + "  " + str(i + 7) + " " + str(count))
            hulls.append(self.hull_from_shapes(shapes[i: (i + 8)]))

        return self.union(hulls)

    # Creates a shape for every 4 shapes entered in shapes
    def triangle_hulls(self, shapes):
        self.print_fu('triangle_hulls()')
        hulls = [cq.Workplane('XY')]
        for i in range(len(shapes) - 2):
            #print(str(i) + "  " + str(i+3) + " " + str(range(len(shapes) - 2)))
            hulls.append(self.hull_from_shapes(shapes[i: (i + 3)]))

        return self.union(hulls)

    # Iterates through all the columns and rows to connect key plate holes together (Georges)
    def connectors(self):
        self.print_fu('connectors()')
        hulls = []
        thickness_mm = self.config.switch_plate_wall_thickness
        col_count = self.config.ncols - 1
        z_sh = self.config.plate_thickness * 0.9# shifts walls of columns 3 and 4 slightly up
        if self.config.use_inner_column:
            col_count = col_count + 1

        # This iteration places the vertical "planks" on the sides of key hole frames
        for column in range(col_count):
            for row in range(self.lastrow):  # need to consider last_row?
            #for row in range(self.config.nrows):  # need to consider last_row?
                places = []
                # The greyed out bits below are in case a keyboard has more than 5 rows and you want to have 1
                # two extra buttons (extra row) under columns 3 and 4. Would need more work.
                #if ((row == self.lastrow) and (column == 2)) or ((column in [1,2,3]) and (row != self.lastrow)): #these columns get different connectors, to avoid "skinny wall" bug


                if (column in [1,2,3]):
                    if column == 1:
                        #x_sh = 0.8 - (0.5 * thickness_mm) # 0.2
                        col_high = column # high and low refer to one key being above the other.
                        col_low = column + 1
                        side_h = "r" # h = high, l = low
                        side_l = "l"
                        z_sh = self.config.plate_thickness / 2
                        x_sh = -self.config.switch_plate_wall_thickness
                    else:
                        #x_sh = 0.8 + (0.5 * thickness_mm) # 1.3
                        side_h = "l"
                        side_l = "r"
                        col_high = column + 1
                        col_low = column
                        z_sh = self.config.plate_thickness / 2
                        x_sh = self.config.switch_plate_wall_thickness

                    places = []
                    places.append(self.get_key_point(col_high, row, "t" + side_h, z_sh = z_sh))
                    places.append(self.get_key_point(col_high, row, "t" + side_h, x_sh = x_sh, z_sh = z_sh))
                    places.append(self.get_key_point(col_high, row, "b" + side_h, x_sh = x_sh, z_sh = z_sh))
                    places.append(self.get_key_point(col_high, row, "b" + side_h, z_sh = z_sh))
                    places.append(self.get_key_point(col_low, row, "b" + side_l,                    z_sh = z_sh))
                    places.append(self.get_key_point(col_low, row, "b" + side_l, x_sh = x_sh,       z_sh = z_sh))
                    places.append(self.get_key_point(col_low, row, "t" + side_l, x_sh = x_sh,       z_sh = z_sh))
                    places.append(self.get_key_point(col_low, row, "t" + side_l,                    z_sh = z_sh))
                    hulls.append(self.hull_from_points(places))
                    places = []

                else:
                    plate = self.config.plate_thickness / 2
                    z_sh = - (self.config.web_thickness / 2) + plate

                    # The original (old) code below is 15x slower than the new code.
                    # Replaced code below by code that generates hulls based on points.
                    # places.append(self.key_place(self.web_post_tl(), column + 1, row))
                    # places.append(self.key_place(self.web_post_tr(), column, row))
                    # places.append(self.key_place(self.web_post_bl(), column + 1, row))
                    # places.append(self.key_place(self.web_post_br(), column, row))
                    #
                    # if len(places): # if arrray is not empty
                    #     hulls.append(self.triangle_hulls(places))
                    #     places = []

                    # new code:
                    places = []
                    places.append(self.get_key_point(column + 1, row, "tl"  , z_sh = plate))
                    places.append(self.get_key_point(column,     row, "tr"  , z_sh = plate))
                    places.append(self.get_key_point(column + 1, row, "bl"  , z_sh = plate))
                    places.append(self.get_key_point(column,     row, "br"  , z_sh = plate))
                    places.append(self.get_key_point(column + 1, row, "tl"  , z_sh = z_sh))
                    places.append(self.get_key_point(column,     row, "tr"  , z_sh = z_sh))
                    places.append(self.get_key_point(column + 1, row, "bl"  , z_sh = z_sh))
                    places.append(self.get_key_point(column,     row, "br"  , z_sh = z_sh))

                    hulls.append(self.hull_from_points(places))
                    # starttime = timeit.default_timer()
                    # print("The time difference method 1 is :", timeit.default_timer() - starttime)

        # This iteration places the horizontal "planks" on the top and bottom of key hole frames
        for column in range(self.config.ncols):
            # for row in range(nrows-1):
            for row in range(self.cornerrow):
                if column == 2: # shift the plank on column 3 slightly to the right. keyframe not symmetrical
                    x_sh_l = -self.config.web_thickness
                    x_sh_r = self.config.web_thickness
                elif column == 3:
                    x_sh_l = 0
                    x_sh_r = self.config.web_thickness
                else:
                    x_sh_l = 0
                    x_sh_r = 0

                z_sh = (self.config.plate_thickness / 2)
                thickness =  -(self.config.web_thickness / 2) + z_sh
                #width =
                places = []
                places.append(self.get_key_point(column, row,   "bl", x_sh= x_sh_l, z_sh=z_sh))
                places.append(self.get_key_point(column, row,   "br", x_sh= x_sh_r, z_sh=z_sh))
                places.append(self.get_key_point(column, row+1, "tl", x_sh= x_sh_l, z_sh=z_sh))
                places.append(self.get_key_point(column, row+1, "tr", x_sh= x_sh_r, z_sh=z_sh))
                places.append(self.get_key_point(column, row+1, "tr", x_sh= x_sh_r, z_sh=thickness))
                places.append(self.get_key_point(column, row+1, "tl", x_sh= x_sh_l, z_sh=thickness))
                places.append(self.get_key_point(column, row,   "br", x_sh= x_sh_r, z_sh=thickness))
                places.append(self.get_key_point(column, row,   "bl", x_sh= x_sh_l, z_sh=thickness))

                # places.append(self.get_key_point(column, row,   "bl", x_sh= x_sh_l, z_sh=z_sh))
                # places.append(self.get_key_point(column, row,   "br", x_sh= x_sh_r, z_sh=z_sh))
                # places.append(self.get_key_point(column, row+1, "tl", x_sh= x_sh_l, z_sh=z_sh))
                # places.append(self.get_key_point(column, row+1, "tr", x_sh= x_sh_r, z_sh=z_sh))
                #
                # places.append(self.get_key_point(column+1, row+1, "tl", x_sh=x_sh_l, z_sh=0))
                # places.append(self.get_key_point(column + 1, row, "bl", x_sh=x_sh_l, z_sh=0))
                # places.append(self.get_key_point(column, row, "bl", x_sh=x_sh_l, z_sh=thickness))
                # places.append(self.get_key_point(column, row + 1, "tl", x_sh=x_sh_l, z_sh=thickness))


                hulls.append(self.hull_from_points(places))
                places = []
        #self.print_model(self.union(hulls), "connectors2nd")

        thickness_mm = self.config.web_thickness
        # This iteration fills up the empty squares between the corners of key hole frames
        # This is the web of thicker frame elements
        for column in range(self.config.ncols - 1):
            # for row in range(nrows-1):  # need to consider last_row?
            for row in range(self.cornerrow):  # need to consider last_row?
                places = []
                if (column in [1,2,3]): # These columns get different connectors to match skinny wall fix
                    if column == 1:
                        # x_sh = 0.8 - (0.5 * thickness_mm) # 0.2
                        col_high = column
                        col_low = column + 1
                        side_h = "r"
                        side_l = "l"
                        z_sh = self.config.plate_thickness / 2
                        x_sh = -self.config.web_thickness#- self.config.switch_plate_wall_thickness #
                    else:
                        # x_sh = 0.8 + (0.5 * thickness_mm) # 1.3
                        side_h = "l"
                        side_l = "r"
                        col_high = column + 1
                        col_low = column
                        z_sh = self.config.plate_thickness / 2
                        x_sh = self.config.web_thickness #self.config.switch_plate_wall_thickness

                    places = []

                    #z_depth = 0#-self.config.web_thickness
                    places.append(self.get_key_point(col_high, row,   "b" + side_h, z_sh=z_sh))
                    places.append(self.get_key_point(col_high, row,   "b" + side_h, x_sh=x_sh, z_sh=z_sh))
                    places.append(self.get_key_point(col_high, row+1, "t" + side_h, x_sh=x_sh, z_sh=z_sh))
                    places.append(self.get_key_point(col_high, row+1, "t" + side_h, z_sh=z_sh))

                    # places.append(self.get_key_point(col_high, row, "b" + side_h, z_sh=-z_sh*2))
                    # places.append(self.get_key_point(col_high, row, "b" + side_h, x_sh=x_sh, z_sh=-z_sh*2))
                    # places.append(self.get_key_point(col_high, row + 1, "t" + side_h, x_sh=x_sh, z_sh=-z_sh*2))
                    # places.append(self.get_key_point(col_high, row + 1, "t" + side_h, z_sh=-z_sh*2))

                    places.append(self.get_key_point(col_low , row,   "b" + side_l, z_sh=z_sh))
                    places.append(self.get_key_point(col_low , row,   "b" + side_l, x_sh=x_sh, z_sh=z_sh))
                    places.append(self.get_key_point(col_low , row+1, "t" + side_l, x_sh=x_sh, z_sh=z_sh))
                    places.append(self.get_key_point(col_low , row+1, "t" + side_l, z_sh=z_sh))

                    hulls.append(self.hull_from_points(places))
                    places = []
                else:
                    places = []
                    z_sh_upward = self.config.plate_thickness / 2
                    z_sh_thickness = - (self.config.web_thickness / 2) + z_sh_upward

                    places.append(self.get_key_point(column,     row,     "br", z_sh=z_sh_upward))
                    places.append(self.get_key_point(column,     row + 1, "tr", z_sh=z_sh_upward))
                    places.append(self.get_key_point(column + 1, row,     "bl", z_sh=z_sh_upward))
                    places.append(self.get_key_point(column + 1, row + 1, "tl", z_sh=z_sh_upward))
                    places.append(self.get_key_point(column,     row,     "br", z_sh=z_sh_thickness))
                    places.append(self.get_key_point(column,     row + 1, "tr", z_sh=z_sh_thickness))
                    places.append(self.get_key_point(column + 1, row,     "bl", z_sh=z_sh_thickness))
                    places.append(self.get_key_point(column + 1, row + 1, "tl", z_sh=z_sh_thickness))

                    hulls.append(self.hull_from_points(places))
                    places = []

                    # slow code: removed.
                    #places.append(self.key_place(self.web_post_br(), column, row))
                    #places.append(self.key_place(self.web_post_tr(), column, row + 1))
                    #places.append(self.key_place(self.web_post_bl(), column + 1, row))
                    #places.append(self.key_place(self.web_post_tl(), column + 1, row + 1))
                    #
                    #if len(places):  # if arrray is not empty
                    #    hulls.append(self.triangle_hulls(places))

        #self.print_model(self.union(hulls), "connectors3rd")

        return self.union(hulls)

    ############
    ## Thumbs ##
    ############

    def thumborigin(self):
        # self.print_fu('thumborigin()')
        # ; this is where the original position of the thumb switches defined.
        # ; each and every thumb keys is derived from this value.
        # ; the value itself is defined from the 'm' key's position in qwerty layout
        # ; and then added by some values, including thumb-offsets above.
        origin = self.key_position([ self.config.mount_width / 2, -(self.config.mount_height / 2), 0], 1, self.cornerrow)
        for i in range(len(origin)):
            origin[i] = origin[i] + self.config.thumb_keys.thumb_offsets[i]
        return origin

    # Thumb key angles / rotation
    # TODO: make angles and locations part of config
    def thumb_tr_place(self, shape):
        self.print_fu('thumb_tr_place()')
        thumb = self.config.thumb_keys
        #shape = self.rotate(shape, [-15, 35, 10]) # rotate [10, -23, 10]
        #print(str(self.config.th.tr_loc))
        shape = self.rotate(shape,  thumb.tr_rot)
        shape = shape.translate(self.thumb_origin)
        #shape = shape.translate([-15, -16, -1]) # move [-12, -16, 3]
        shape = shape.translate(    thumb.tr_loc)
        return shape

    def thumb_tl_place(self, shape):
        self.print_fu('thumb_tl_place()')
        thumb = self.config.thumb_keys
        shape = self.rotate(shape,  thumb.tl_rot ) # rotate [10, -23, 10]
        shape = shape.translate(self.thumb_origin)
        shape = shape.translate(    thumb.tl_loc )# move [-32, -15, -2]
        return shape

    def thumb_mr_place(self, shape):
        self.print_fu('thumb_mr_place()')
        thumb = self.config.thumb_keys
        shape = self.rotate(shape,  thumb.mr_rot)
        shape = shape.translate(self.thumb_origin)
        shape = shape.translate(    thumb.mr_loc)
        return shape

    def thumb_ml_place(self, shape):
        self.print_fu('thumb_ml_place()')
        thumb = self.config.thumb_keys
        shape = self.rotate(shape,  thumb.ml_rot)
        shape = shape.translate(self.thumb_origin)
        shape = shape.translate(    thumb.ml_loc)
        return shape

    def thumb_br_place(self, shape):
        self.print_fu('thumb_br_place()')
        thumb = self.config.thumb_keys
        shape = self.rotate(shape,  thumb.br_rot)
        shape = shape.translate(self.thumb_origin)
        shape = shape.translate(    thumb.br_loc)
        return shape

    def thumb_bl_place(self, shape):
        self.print_fu('thumb_bl_place()')
        thumb = self.config.thumb_keys
        shape = self.rotate(shape,  thumb.bl_rot)
        shape = shape.translate(self.thumb_origin)
        shape = shape.translate(    thumb.bl_loc)
        return shape

    # not sure what this does? Draws caps?
    def thumb_1x_layout(self, shape, cap=False):
        self.print_fu('thumb_1x_layout()')
        thumb_count = self.config.thumb_count

        if thumb_count == 0:    # TODO
            shapes = cq.Workplane("XY")
        elif thumb_count == 1:  # TODO
            shapes = cq.Workplane("XY")
        elif thumb_count == 2:  # TODO
            shapes = cq.Workplane("XY")
        elif thumb_count == 3:  # TODO
            shapes = cq.Workplane("XY")
        elif thumb_count == 4:
            if cap:
                shapes = self.thumb_mr_place(shape)
                shapes = shapes.add(self.thumb_ml_place(shape))
            else:
                shapes = self.union(
                    [
                        self.thumb_mr_place(shape),
                        self.thumb_ml_place(shape),
                    ])
        elif thumb_count == 5:
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
                    ])
        else:
            self.print_debug("Thumb count too high, no algorithm implemented for such high thumb count.")
            os.exit

        return shapes

    def thumb_15x_layout(self, shape, cap=False):
        self.print_fu('thumb_15x_layout()')
        thumb_count = self.config.thumb_count
        if thumb_count == 3:
            if cap:
                shape = self.rotate(shape, (0, 0, 90))
                return self.thumb_tr_place(shape).add(self.thumb_tl_place(shape).solids().objects[0]).add(self.thumb_ml_place(shape).solids().objects[0])
            else:
                return self.thumb_tr_place(shape).union(self.thumb_tl_place(shape)).union(self.thumb_ml_place(shape))
        #elif thumb_count == 5:

        # The code below places the 2 highest thumb key frames/plates closest to the keyboard.
        if cap:
            shape = self.rotate(shape, (0, 0, 90))
            return self.thumb_tr_place(shape).add(self.thumb_tl_place(shape).solids().objects[0])
        else:
            return self.thumb_tr_place(shape).union(self.thumb_tl_place(shape))

        # else:

        return shape

    def double_plate(self):
        ################
        ## SA Keycaps ##
        ################
        #sa_length = 18.25
        thumb_plate_len = self.config.thumb_plate_length # 37.5
        # 40
        self.print_fu('double_plate()')
        plate_height = (thumb_plate_len - self.config.keycap_space) / 2 #7.. 33
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
        a = self.keyswitch_frame_width #+ 0.1
        keyswitch_frame_widths = (a, a, a, a)
        shape = self.thumb_1x_layout(self.single_plate(keyswitch_frame_widths))
        # changed from shape = shape.union(self.thumb_15x_layout(self.single_plate()))
        shape = shape.union(self.thumb_15x_layout(self.rotate(self.single_plate(keyswitch_frame_widths), [0,0, 0]))) # last 0 was (pi / 2.00)
        shape = shape.union(self.thumb_15x_layout(self.double_plate()))

        return shape

    # The thumb post functions generate a 3D shape
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

    # this function seems to generate the top part of the thumb switch frames (excluding the wall)
    def thumb_connectors(self):
        self.print_fu('thumb_connectors()')
        hulls = []
        thumb_count = self.config.thumb_count
        conn_thickness = self.config.switch_plate_wall_thickness
        #if thumb_count == 0:    # TODO

        if thumb_count == 1:  # TODO
            print("top right")
            # Top right
            hulls.append(
                self.triangle_hulls(
                    [
                        self.thumb_tl_place(self.thumb_post_tr()),
                        self.thumb_tl_place(self.thumb_post_br()),
                    ]
                )
            )

        if thumb_count >= 2:  # TODO
            print("top left")
            thickness_mm = self.config.switch_plate_wall_thickness
            x_sh_col1 = 0.7 - (0.5 * thickness_mm) # shift in the x direction for column 1 connectors
            x_sh_col2 = 0.7 + (0.5 * thickness_mm)  # shift in the x direction for column 2 connectors
            x_sh_col3 = 1.7
            y_sh = 0.3
            z_sh = self.config.plate_thickness

            # This does the connector between the two thumb key hole frames
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
            # top two to the main keyboard, starting on the left
            # TODO: fix conditionals to create correct thumb cluster connectors depending on row and column count
            # this code assumes no extra row under column 3 and 4
            # last row = number of rows -1 | corner row = number of rows - 2
            if self.config.nrows > 5:
                thumb_last_row = self.lastrow
                thumb_corner_row = self.cornerrow
            else:
                thumb_last_row = self.lastrow
                thumb_corner_row = self.cornerrow
            # Triangles from the right edge of the thumb key cluster to the 3rd column:
            hulls.append(
                self.triangle_hulls(
                    [
                        #; top two thumb keys to the main keyboard, starting on the left going to the right
                        # thumb_tl/tr refer to the entire left and right thumb keys (not to left or right connector)
                        self.thumb_tl_place(self.thumb_post_tl()),
                        self.key_place(self.web_post_bl(), 0, thumb_corner_row),
                        self.thumb_tl_place(self.thumb_post_tr()),
                        self.key_place(self.web_post_br(), 0, thumb_corner_row),
                        self.thumb_tr_place(self.thumb_post_tl()),
                        self.key_place(self.web_post_bl(), 1, thumb_corner_row),
                          # 2cornerrow  #  1 You'll have to mess around with this number as you move the thumb clusters back and forward by more than a few mm

# TODO : adjustments toevoegen aan _g() functies. Toevoegen in _g zelf?
                        # The code below is for the "triangle shaped plate" next to the thumb switches

                        # "lip" from thumb keys to thumb key walls
                        self.thumb_tr_place(self.thumb_post_tr()),
                        self.key_place(self.web_post_br_g(conn_thickness), 1, thumb_corner_row, x_sh_col1, y_sh, z_sh),
                        # self.thumb_tr_place(self.thumb_post_br()),
                        # self.key_place(self.web_post_bl_g(conn_thickness), 2, thumb_corner_row, x_sh_col1, y_sh, z_sh), #2 connection from 2nd thumb right wall to 2nd column wall
                        # self.thumb_tr_place(self.thumb_post_br()),
                        # self.key_place(self.web_post_br_g(conn_thickness), 2, thumb_corner_row, x_sh_col2, y_sh, z_sh), # by G to make triangle thicker
                        #
                        #
                        # self.key_place(self.web_post_br_g(conn_thickness), 2, thumb_corner_row, x_sh_col2, 0, -0.2), # by G to make triangle thicker
                        #
                        # self.key_place(self.web_post_bl_g(conn_thickness), 2, thumb_corner_row, x_sh_col2, 0, -4), #2 self.lastrow
                        # self.key_place(self.web_post_br_g(conn_thickness), 2, thumb_corner_row, x_sh_col2, 0, -4), #2 self.lastrow
                        # # The point that connects the "triangle" next to the thumb keys to the keyboard (right wall 3rd column)
                        # self.thumb_tr_place(self.thumb_post_br()),
                        # self.key_place(self.web_post_bl_g(conn_thickness), 3, thumb_corner_row, x_sh_col3), # was 3 #self.lastrow
                    ]
                ))


            # # right most triangles?
            # hulls.append(
            #     self.triangle_hulls(
            #         [   # important note: assuming 7 column 6 row config for example:
            #             # column 1 and 2 have 5 rows (+ thumb rows),
            #             # column 3 and 4 have 6 rows.
            #             # colums after 5 have 5 rows again TODO: this all depends on use_inner_column and/or last_row_count (zero, full etc)
            #             self.key_place(self.web_post_tl(), 2, thumb_last_row),   #self.lastrow
            #             self.key_place(self.web_post_bl(), 2, thumb_corner_row),  #self.cornerrow
            #             self.key_place(self.web_post_tr(), 2, thumb_last_row),    #self.lastrow
            #             self.key_place(self.web_post_br(), 2, thumb_corner_row),  #self.cornerrow
            #             self.key_place(self.web_post_bl(), 3, thumb_corner_row), #  3 cornerrow
            #         ]
            #     )
            # )

        # if thumb_count == 3:  # TODO
        #
        # if thumb_count == 4:  # TODO
        #
        # if thumb_count == 5:  # TODO
        if thumb_count == 6:
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
                        self.key_place(self.web_post_bl(), 0, self.cornerrow),
                        self.thumb_tl_place(self.thumb_post_tr()),
                        self.key_place(self.web_post_br(), 0, self.cornerrow),
                        self.thumb_tr_place(self.thumb_post_tl()),
                        self.key_place(self.web_post_bl(), 1, self.cornerrow),
                        self.thumb_tr_place(self.thumb_post_tr()),
                        self.key_place(self.web_post_br(), 1, self.cornerrow),
                        self.key_place(self.web_post_tl(), 2, self.lastrow),
                        self.key_place(self.web_post_bl(), 2, self.lastrow),
                        self.thumb_tr_place(self.thumb_post_tr()),
                        self.key_place(self.web_post_bl(), 2, self.lastrow),
                        self.thumb_tr_place(self.thumb_post_br()),
                        self.key_place(self.web_post_br(), 2, self.lastrow),
                        self.key_place(self.web_post_bl(), 3, self.lastrow),
                        self.key_place(self.web_post_tr(), 2, self.lastrow),
                        self.key_place(self.web_post_tl(), 3, self.lastrow),
                        self.key_place(self.web_post_bl(), 3, self.cornerrow),
                        self.key_place(self.web_post_tr(), 3, self.lastrow),
                        self.key_place(self.web_post_br(), 3, self.cornerrow),
                        self.key_place(self.web_post_bl(), 4, self.cornerrow),
                    ]
                )
            )

            hulls.append(
                self.triangle_hulls(
                    [
                        self.key_place(self.web_post_br(), 1, self.cornerrow),
                        self.key_place(self.web_post_tl(), 2, self.lastrow),
                        self.key_place(self.web_post_bl(), 2, self.cornerrow),
                        self.key_place(self.web_post_tr(), 2, self.lastrow),
                        self.key_place(self.web_post_br(), 2, self.cornerrow),
                        self.key_place(self.web_post_bl(), 3, self.cornerrow),
                    ]
                )
            )

            hulls.append(
                self.triangle_hulls(
                    [
                        self.key_place(self.web_post_tr(), 3, self.lastrow),
                        self.key_place(self.web_post_br(), 3, self.lastrow),
                        self.key_place(self.web_post_tr(), 3, self.lastrow),
                        self.key_place(self.web_post_bl(), 4, self.cornerrow),
                    ]
                )
            )
        if thumb_count > 6:
            self.print_debug("This thumb count is not implemented yet.")
            os.exit

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

	# left most row position? Not sure Georges
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
        return [dx * self.config.wall_thickness, # x
                dy * self.config.wall_thickness, # y
                -1]                              # z

    def wall_locate2(self, dx, dy):
        self.print_fu("wall_locate2()")
        return [dx * self.config.wall_xy_offset,
                dy * self.config.wall_xy_offset,
                self.config.wall_z_offset]

    def wall_locate3(self, dx, dy):
        self.print_fu("wall_locate3()")
        return [dx * (self.config.wall_xy_offset + self.config.wall_thickness), # width of keyboard (higher number places walls further out)
                dy * (self.config.wall_xy_offset + self.config.wall_thickness), # depth of keyboard
                self.config.wall_z_offset]

   #  "If you want to change the wall, use this.
   # place1 means the location at the keyboard, marked by key-place or thumb-xx-place
   # dx1 means the movement from place1 in x coordinate, multiplied by wall-xy-locate.
   # dy1 means the movement from place1 in y coordinate, multiplied by wall-xy-locate.
   # post1 means the position this wall attached to place1.
   #       xxxxx-br means bottom right of the place1.
   #       xxxxx-bl means bottom left of the place1.
   #       xxxxx-tr means top right of the place1.
   #       xxxxx-tl means top left of the place1.
   # place2 means the location at the keyboard, marked by key-place or thumb-xx-place
   # dx2 means the movement from place2 in x coordinate, multiplied by wall-xy-locate.
   # dy2 means the movement from place2 in y coordinate, multiplied by wall-xy-locate.
   # post2 means the position this wall attached to place2.
   #       xxxxx-br means bottom right of the place2.
   #       xxxxx-bl means bottom left of the place2.
   #       xxxxx-tr means top right of the place2.
   #       xxxxx-tl means top left of the place2.
   # How does it work?
   # Given the following wall (side cross section view)
   #     a ==\\ b
   #          \\
   #         c \\ d
   #           | |
   #           | |
   #           | |
   #           | |
   #         e | | f
   # In this function a: usually the wall of a switch hole.
   #                  b: the result of hull and translation from wall-locate1
   #                  c: the result of hull and translation from wall-locate2
   #                  d: the result of hull and translation from wall-locate3
   #                  e: the result of bottom-hull translation from wall-locate2
   #                  f: the result of bottom-hull translation from wall-locate3"
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
            shape = shape.union(self.key_wall_brace(x, 0, 0, 1, self.web_post_tl(), x - 1, 0, 0, 1, self.web_post_tr()
            ))
        shape = shape.union(self.key_wall_brace(
            self.lastcol, 0, 0, 1, self.web_post_tr(), self.lastcol, 0, 1, 0, self.web_post_tr()
        ))
        return shape

    def right_wall(self):
        self.print_fu("right_wall()")
        y = 0
        shape = cq.Workplane('XY')
        shape = shape.union(
            self.key_wall_brace(
                self.lastcol, y, 1, 0, self.web_post_tr(),
                self.lastcol, y, 1, 0, self.web_post_br()
            )
        )
        for i in range(self.lastrow - 1):
            y = i + 1
            shape = shape.union(self.key_wall_brace(
                self.lastcol, y, 1, 0, self.web_post_tr(),
                self.lastcol, y, 1, 0, self.web_post_br()
            ))
            shape = shape.union(self.key_wall_brace(
                self.lastcol, y, 1, 0, self.web_post_br(),
                self.lastcol, y - 1, 1, 0, self.web_post_tr()
            ))

        shape = shape.union(self.key_wall_brace(
            self.lastcol, self.cornerrow, 0, -1, self.web_post_br(),
            self.lastcol, self.cornerrow, 1, 0, self.web_post_br(),
        ))
        return shape

    def left_wall(self):
        self.print_fu('left_wall()')
        shape = cq.Workplane('XY')
        shape = shape.union(self.wall_brace(
            (lambda sh: self.key_place(sh, 0, 0)), 0, 1, self.web_post_tl(),
            (lambda sh: self.left_key_place(sh, 0, 1)), 0, 1, self.web_post(),
        ))

        shape = shape.union(self.wall_brace(
            (lambda sh: self.left_key_place(sh, 0, 1)), 0, 1, self.web_post(),
            (lambda sh: self.left_key_place(sh, 0, 1)), -1, 0, self.web_post(),
        ))

        for i in range(self.lastrow):
            y = i
            temp_shape1 = self.wall_brace(
                (lambda sh: self.left_key_place(sh, y, 1)), -1, 0, self.web_post(),
                (lambda sh: self.left_key_place(sh, y, -1)), -1, 0, self.web_post(),
            )
            temp_shape2 = self.hull_from_shapes((
                self.key_place(self.web_post_tl(), 0, y),
                self.key_place(self.web_post_bl(), 0, y),
                self.left_key_place(self.web_post(), y, 1),
                self.left_key_place(self.web_post(), y, -1),
            ))
            shape = shape.union(temp_shape1)
            shape = shape.union(temp_shape2)

        for i in range(self.lastrow - 1):
            y = i + 1
            temp_shape1 = self.wall_brace(
                (lambda sh: self.left_key_place(sh, y - 1, -1)), -1, 0, self.web_post(),
                (lambda sh: self.left_key_place(sh, y, 1)), -1, 0, self.web_post(),
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

    # The code below determines how the front wall is made (wall with thumb switches)
    def front_wall(self):
        self.print_fu('front_wall()')
        shape = cq.Workplane('XY')
        thickness = self.config.wall_thickness
        if self.config.last_row_count == "zero":
            front_wall_row = self.cornerrow
            thumb_tr_post = self.thumb_post_br()
        elif self.config.last_row_count == "full":
            front_wall_row = self.lastrow
            thumb_tr_post = self.thumb_post_br()
        # TODO: implement self.config.last_row_count == "two" ??

        # shape = shape.union(
        #     self.key_wall_brace(
        #         #self.lastcol, 0, 0, 1, self.web_post_tl(), self.lastcol, 0, 1, 0, self.web_post_tl()
        #         self.lastcol, 0, 0, 1, self.web_post_tr(), self.lastcol, 0, 1, 0, self.web_post_tr()
        #     )
        # )

        # TODO thumb-tr-post (if (= (get c :configuration-thumb-count) :five ) web-post-br thumb-post-br)]
        # ;The code below determines how the front wall is made (wall with thumb switches)

        # this generates the front wall next to the thumb keys (column 3)
        shape = shape.union(self.wall_brace(
            self.thumb_tr_place, 0, -1, thumb_tr_post,
            (lambda sh: self.key_place(sh, 3, front_wall_row)), 0, -1, self.web_post_bl()
        ))
        #

        # Wall along 4th column and along 4 - 5 column connector
        shape = shape.union(self.key_wall_brace(
            3, front_wall_row, 0, -1, self.web_post_bl(),
            3, front_wall_row, 0.5, -1, self.web_post_br()
        ))
        shape = shape.union(self.key_wall_brace(
            3, front_wall_row, 0.5, -1, self.web_post_br(),
            4, front_wall_row, 0, -1, self.web_post_bl() # 1, -1
        ))
        # The below for-loops ar for the last few columns (last 3 columns in case of 7 columns)
        for i in range(self.config.ncols - 4):
            x = i + 4
            shape = shape.union(self.key_wall_brace(
                x, front_wall_row, 0, -1, self.web_post_bl(),
                x, front_wall_row, 0, -1, self.web_post_br()
            ))
        for i in range(self.config.ncols - 5):
            x = i + 5
            shape = shape.union(self.key_wall_brace(
                x, front_wall_row, 0, -1, self.web_post_bl(),
                x - 1, front_wall_row, 0, -1, self.web_post_br()
            ))
        
        return shape

    # creates the front facing part of the front wall of thumb cluster
    # The side facing parts of the front wall are generated in some other function
    def thumb_walls(self):
        self.print_fu('thumb_walls()')
        # thumb, walls
        shape = cq.Workplane('XY')
        thickness = self.config.wall_thickness
        thumb_count = self.config.thumb_count

        wall_brace = self.wall_brace

        # Comments below are from the perspective of the right keyboard
        # Code below generates the walls of the thumb keys
        if thumb_count == 2:
            # Front facing wall of the right most thumb key
            shape = shape.union(wall_brace(self.thumb_tr_place, 0, -1, self.thumb_post_br(),
                                           self.thumb_tr_place, 0, -1, self.thumb_post_bl()))
            # Front facing "pillar" of the right most thumb key (to the left of the one from the code above)
            shape = shape.union(wall_brace(self.thumb_tr_place, 0, -1, self.thumb_post_bl(),
                                           self.thumb_tl_place, 0, -1, self.thumb_post_br()))
            # Front facing wall of the left most thumb key
            shape = shape.union(wall_brace(self.thumb_tl_place, 0, -1, self.thumb_post_br(),
                                           self.thumb_tl_place, 0, -1, self.thumb_post_bl()))
            # Front facing left most angle of left most thumb key
            shape = shape.union(wall_brace(self.thumb_tl_place, 0, -1, self.thumb_post_bl(),
                                           self.thumb_tl_place, -1, 0, self.thumb_post_bl()))
            # Left wall of left most thumb key
            shape = shape.union(wall_brace(self.thumb_tl_place, -1, 0, self.thumb_post_bl(),
                                           self.thumb_tl_place, -1, 0, self.thumb_post_tl()))
        else: # TODO: implement other thumb counts code below is for either 5 or 6 thumb switches
            shape = shape.union(self.wall_brace(self.thumb_mr_place, 0, -1, self.web_post_br(),
                                                self.thumb_tr_place, 0, -1, self.thumb_post_br()))
            shape = shape.union(self.wall_brace(self.thumb_mr_place, 0, -1, self.web_post_br(),
                                                self.thumb_mr_place, 0, -1, self.web_post_bl()))
            shape = shape.union(self.wall_brace(self.thumb_br_place, 0, -1, self.web_post_br(),
                                                self.thumb_br_place, 0, -1, self.web_post_bl()))
            shape = shape.union(self.wall_brace(self.thumb_ml_place, -0.3, 1, self.web_post_tr(),
                                                self.thumb_ml_place, 0, 1, self.web_post_tl()))
            shape = shape.union(self.wall_brace(self.thumb_bl_place, 0, 1, self.web_post_tr(),
                                                self.thumb_bl_place, 0, 1, self.web_post_tl()))
            shape = shape.union(self.wall_brace(self.thumb_br_place, -1, 0, self.web_post_tl(),
                                                self.thumb_br_place, -1, 0, self.web_post_bl()))
            shape = shape.union(self.wall_brace(self.thumb_bl_place, -1, 0, self.web_post_tl(),
                                                self.thumb_bl_place, -1, 0, self.web_post_bl()))
            # thumb, corners
            shape = shape.union(self.wall_brace(self.thumb_br_place, -1, 0, self.web_post_bl(),
                                                self.thumb_br_place, 0, -1, self.web_post_bl()))
            shape = shape.union(self.wall_brace(self.thumb_bl_place, -1, 0, self.web_post_tl(),
                                                self.thumb_bl_place, 0, 1, self.web_post_tl()))
            # thumb, tweeners
            shape = shape.union(self.wall_brace(self.thumb_mr_place, 0, -1, self.web_post_bl(),
                                                self.thumb_br_place, 0, -1, self.web_post_br()))
            shape = shape.union(self.wall_brace(self.thumb_ml_place, 0, 1, self.web_post_tl(),
                                                self.thumb_bl_place, 0, 1, self.web_post_tr()))
            shape = shape.union(self.wall_brace(self.thumb_bl_place, -1, 0, self.web_post_bl(),
                                                self.thumb_br_place, -1, 0, self.web_post_tl()))
            shape = shape.union(self.wall_brace(self.thumb_tr_place, 0, -1, self.thumb_post_br(),
                                                (lambda sh: self.key_place(sh, 3, self.lastrow)), 0, -1, self.web_post_bl(), ))

        return shape

    # The left side of the thumb cluster that connects to the rest of the keyboard (as seen from the right side keyboard)
    # TODO: work in progress porting from manuform.clj (defn second-thumb-to-body
    def thumb_connection(self):
        self.print_fu('thumb_connection()')
        shape = cq.Workplane('XY')
        # clunky bit on the top left thumb connection  (normal connectors don't work well)

        # shape = shape.union(self.bottom_hull(
        #     [
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
        #         self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate2(-0.3, 1))),
        #         self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate3(-0.3, 1))),
        #     ]
        # ))

        # body-gap-default
        # TODO: add use_inner_column and thumbcount functionality from clojure script
        # shape = shape.union(self.bottom_hull(
        #     [
        #         self.thumb_ml_place(self.translate(self.thumb_post_tr(), self.wall_locate2(-0.3, 1))),
        #         self.thumb_ml_place(self.translate(self.thumb_post_tr(), self.wall_locate3(-0.3, 1))),
        #     ]
        # ))

        use_inner_column = self.config.use_inner_column
        # body-gap-two
        # TODO: add use_inner_column and thumbcount functionality from clojure script
        shape = shape.union(self.bottom_hull(
            [
                self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
                self.thumb_tl_place(self.translate(self.thumb_post_tl(), self.wall_locate2(-1, 0))),
                self.thumb_tl_place(self.translate(self.thumb_post_tl(), self.wall_locate3(-1, 0))),
            ]
        ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
            ]
        ))

        if self.config.thumb_count == 2:
            shape = shape.union(self.hull_from_shapes(
                [
                    self.thumb_tl_place(self.translate(self.thumb_post_tl(), self.wall_locate3(-1, 0))),
                ]
            ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.left_key_place(self.web_post(), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))

        shape = shape.union(self.hull_from_shapes(
            [
                self.left_key_place(self.web_post(), self.cornerrow, -1),
                self.left_key_place(self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.cornerrow, -1),
                self.key_place(self.web_post_bl(), 0, self.cornerrow),
                self.key_place(self.translate(self.web_post_bl(), self.wall_locate1(-1, 0)), 0, self.cornerrow),
                self.thumb_tl_place(self.thumb_post_tl()),
            ]
        ))
        places = []
        if self.config.last_row_count == "zero":
            cornerrow = self.cornerrow
        else:
            cornerrow = self.lastrow

        z_plate = self.config.plate_thickness / 2
        z_thumb_plate = self.config.wall_thickness - self.config.plate_thickness
        #z_key_bot = self.config.wall_thickness - self.config.plate_thickness
        # Triangle next to thumb keys
        places.append(self.get_thumb_point("tr_thumb", "tr", z_sh = -z_thumb_plate))
        places.append(self.get_thumb_point("tr_thumb", "br", z_sh = -z_thumb_plate))
        places.append(self.get_key_point(3, cornerrow, "bl"))
        places.append(self.get_key_point(3, cornerrow, "bl", z_sh=  z_plate))
        places.append(self.get_thumb_point("tr_thumb", "tr", z_sh = self.config.plate_thickness))
        places.append(self.get_thumb_point("tr_thumb", "br", z_sh = self.config.plate_thickness))

        shape = shape.union(self.hull_from_points(places))
        places = []
        # # TODO: thumb count default?
        # shape = shape.union(self.hull_from_shapes(
        #     [
        #         self.thumb_ml_place(self.web_post_tr()),
        #         self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate1(-0.4, 1))), #was tr
        #         self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate2(-0.4, 1))), #was tr
        #         self.thumb_ml_place(self.translate(self.web_post_tr(), self.wall_locate3(-0.4, 1))), #was tr
        #         self.thumb_tl_place(self.thumb_post_tl()),
        #     ]
        # ))

        # shape = shape.union(
        #     self.hull_from_shapes(
        #         [
        #             self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
        #             self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
        #             self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate2(-0.3, 1))),
        #             self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate3(-0.3, 1))),
        #             self.thumb_tl_place(self.thumb_post_tl()),
        #         ]
        #     )
        # )  # )
        #
        # shape = shape.union(self.hull_from_shapes(
        #     [
        #         self.left_key_place(self.web_post(), self.cornerrow, -1),
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.cornerrow, -1),
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate2(-1, 0)), self.cornerrow, -1),
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate3(-1, 0)), self.cornerrow, -1),
        #         self.thumb_tl_place(self.thumb_post_tl()),
        #     ]
        # ))
        #
        # shape = shape.union(self.hull_from_shapes(
        #     [
        #         self.left_key_place(self.web_post(), self.cornerrow, -1),
        #         self.left_key_place(self.translate(self.web_post(), self.wall_locate1(-1, 0)), self.cornerrow, -1),
        #         self.key_place(self.web_post_br(), 0, self.cornerrow),
        #         self.key_place(self.translate(self.web_post_br(), self.wall_locate1(-1, 0)), 0, self.cornerrow),
        #         self.thumb_tl_place(self.thumb_post_tl()),
        #     ]
        # ))
        #
        # shape = shape.union(self.hull_from_shapes(
        #     [
        #         self.thumb_ml_place(self.web_post_tl()),
        #         self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate1(-0.3, 1))),
        #         self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate2(-0.3, 1))),
        #         self.thumb_ml_place(self.translate(self.web_post_tl(), self.wall_locate3(-0.3, 1))),
        #         self.thumb_tl_place(self.thumb_post_tl()),
        #     ]
        # ))

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
                # pinky wall
                # pinky connectors
                self.thumb_walls(),
                self.thumb_connection(), #in clojure script: (second-thumb-to-body c)  ; thumb cluster front inner/corner wall (near b button)
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
        shift_right = column == self.lastcol
        shift_left = column == 0
        shift_up = (not (shift_right or shift_left)) and (row == 0)
        shift_down = (not (shift_right or shift_left)) and (row >= self.lastrow)

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
            self.screw_insert(0, self.lastrow, bottom_radius, top_radius, height),
            self.screw_insert(2, self.lastrow + 0.3, bottom_radius, top_radius, height),
            self.screw_insert(3, 0, bottom_radius, top_radius, height),
            self.screw_insert(self.lastcol, 1, bottom_radius, top_radius, height),
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

        for column in range(self.lastcol):
            for row in range(self.lastrow - 1):
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
        #shape = self.key_holes()
        #self.print_model(shape, "key_holes")

        # Connect the key switch frames together with extra material
        # This generates the top surface of the keyboard.

        shape = shape.union(self.connectors())
        #self.print_model(shape, "key_hole_connectors")

        ## Generate the thumb switch frames
        shape = shape.union(self.thumb())
        #self.print_model(shape, "thumb_switches")
        ## Generate the material between the thumb switch frames and the top surface
        shape = shape.union(self.thumb_connectors())
        self.print_model(shape, "thumb_conn")

        # Generate the vertical outer walls.
        s2 = cq.Workplane('XY').union(self.case_walls())
        self.print_model(s2, "walls")
        # Generate screw insert cilinders (without hole)

        #s2 = self.union([s2, *self.screw_insert_outers])
        #self.print_model(s2, "screw_insert_cil")
        
        # TODO: add switch for Teensy or USB holder setting?
        ## s2 = s2.union(self.teensy_holder())
        #s2 = s2.union(self.usb_holder())
        #self.print_model(s2, "usb holder")

        # Connector holes
        #s2 = s2.cut(self.rj9_space())
        #self.print_model(s2, "s2 cut out rj9 space")
        #s2 = s2.cut(self.usb_holder_hole())
        #self.print_model(s2, "s2 cut out usb space")

        # Create holes in the screw insert cilinders
        #s2 = s2.cut(self.union(self.screw_insert_holes))
        #self.print_model(s2, "s2 cut out screw holes")

        # Add rj9 holder to shape
        ##shape = shape.union(self.rj9_holder()) # georges fix deleted.
        #s2 = s2.union(self.rj9_holder())
        #self.print_model(s2, "add rj9 holder to shape")

        # Add s2 to shape
        #shape = shape.union(s2, tol=.01)
        try:
            #shape = shape.union(s2, tol=.01)
            #self.print_model(shape, "add s2 to shape")
            print("add s2 disabled")
        except Exception:
            traceback.print_exc()
            sys.exit()

        # TODO: add switch for wire posts setting?
        # shape = shape.union(wire_posts())

        # Create a box shape that is substraced from the model to
        # cut the keyboard along the XY plane (the box is substracted from model)
        block = cq.Workplane("XY").box(500, 500, 40)
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



