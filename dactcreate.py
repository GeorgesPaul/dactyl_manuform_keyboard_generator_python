# Written for Python > 3.9

import cadquery as cq

import numpy as np
from numpy import pi
import os.path as path
import dactylutils
import os

from scipy.spatial import ConvexHull as sphull

# comments below are from the perspective of the right keyboard
# The code below creates a conf_right_keyboard data-object that holds keyboard customization parameters.
conf_right_keyboard = dactylutils.Dact.Config(show_caps   = False,
                                              script_print_shapes = True,
                                              nrows      = 6,
                                              ncols      = 7,  # row 3 from top, 3 from bottom should have 8 cols on right
                                              thumb_count = 2,
                                              extra_width   =   3, # extra width between row keys
                                              wall_z_offset = -15,  # Depth (downwards) of the first wall-slope from the top of the keyboard.
                                              wall_xy_offset = 5,  # Width (sideways) of the first wall-slope from the top of the keyboard.
                                              left_wall_x_offset = 10,  # Same as above for the left wall
                                              left_wall_z_offset = 2,   # Same as above for the left wall
                                              wall_thickness = 1.5,
                                              #thumb_offsets = [10, -3, -3], # causes freeze?
                                              #plate_thickness = 2
                                              )

# Create keyboard object in memory with desired config settings
# Note: this is the programmatic object. Not the 3D model object yet.
dact_right = dactylutils.Dact(conf_right_keyboard)

# Generate the 3D model
mod_r = dact_right.model_right()

# Store the 3D model on disk
filename_right = path.join("things", r"right_og_py.step")
cq.exporters.export(w=mod_r, fname=filename_right, exportType='STEP')

# Print file name location of 3D model(s)
print(os.open(filename_right, os.O_RDONLY))



#dct_right_no_bottom = dactylutils.Dact().Config(show_caps = False)
#dct_left_no_bottom = dactylutils.Dact()



#base = baseplate(model_right())
#show_object(base)

#show_object(model_right())

#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.step"), exportType='STEP')
#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.dxf"), exportType='DXF')