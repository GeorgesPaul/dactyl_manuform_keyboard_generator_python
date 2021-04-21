# Written for Python > 3.9

import cadquery as cq

import numpy as np
from numpy import pi
import os.path as path
from dactylutils import Dact
from dataclasses import dataclass, fields
import os

from scipy.spatial import ConvexHull as sphull

# Example on how to generate Dactyl Manuform CAD files: 
def main():
	# comments below are from the perspective of the right keyboard
	# The code below creates a conf_right_keyboard data-object that holds keyboard customization parameters.
	conf_right_keyboard = Dact.Config(show_caps   = False,
									  script_print_shapes = True,  # prints intermediate shapes (to see how script builds up 3D model)
									  script_verbose_func = False, # prints debug info (function names)
									  nrows      = 6,
									  ncols      = 7,  # row 3 from top, 3 from bottom should have 8 cols on right
									  thumb_count = 2, # number of thumb keys on thumb "isle"
									  #extra_width   =  2.5,   # extra space between key rows (extra vertical space only). Can't be lower than 2
									  #extra_height  =  1,   # extra space between key columns (extra horizontal space). Can't be lower than 1
									  wall_z_offset = -15,  # Depth (downwards) of the first wall-slope from the top of the keyboard.
									  wall_xy_offset = 5,   # Width (sideways) of the first wall-slope from the top of the keyboard.
									  left_wall_x_offset = 10,  # Same as above for the left wall
									  left_wall_z_offset = 2,   # Same as above for the left wall
									  wall_thickness    = 2,
									  switch_plate_wall_thickness = 2,
									  web_thickness     = 3,        # Note: should be higher than plate_thickness.
									  plate_thickness   = 0.95,     # The key switch plate thickness. For Cherry MX chose 1mm
									  #thumb_offsets = [10, -3, -3], # causes freeze?
									  #plate_thickness = 2
									  #th.tr_angle = [-15, 35, 10]
									  #th = {fields(dactylutils.Dact.Config.ThumbKey).tr_loc: [-15, 35, 10]},
										thumb_keys = Dact.Config.ThumbKeys(
											tr_rot=[-15, 35, 10],
											tr_loc=[-15, -16, -1],
											tl_rot=[-15, 50, 10],
											tl_loc=[-35, -15, 10],
													)
												  )

	# Create keyboard object in memory with desired config settings
	# Note: this is the programmatic object. Not the 3D model object yet.
	dact_right = Dact(conf_right_keyboard)

	# # Generate the 3D model
	mod_r = dact_right.model_right()
	#
	# # Store the 3D model on disk
	# filename_right = path.join("things", r"right_og_py.step")
	# cq.exporters.export(w=mod_r, fname=filename_right, exportType='STEP')
	#
	# # Print file name location of 3D model(s)
	# print(os.open(filename_right, os.O_RDONLY))



	#dct_right_no_bottom = dactylutils.Dact().Config(show_caps = False)
	#dct_left_no_bottom = dactylutils.Dact()



	#base = baseplate(model_right())
	#show_object(base)

	#show_object(model_right())

	#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.step"), exportType='STEP')
	#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.dxf"), exportType='DXF')

main()