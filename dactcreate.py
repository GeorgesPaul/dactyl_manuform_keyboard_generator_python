# Written for Python > 3.9

import cadquery as cq

import numpy as np
from numpy import pi
import os.path as path
import dactylutils
import os

from scipy.spatial import ConvexHull as sphull

conf1 = dactylutils.Dact.Config(show_caps   = True,
                                script_print_shapes = True,
                                 nrows      = 5,
                                 ncols      = 6,
                                 )

dact_right = dactylutils.Dact(conf1)

mod_r = dact_right.model_right()

filename_right = path.join("things", r"right_og_py.step")
cq.exporters.export(w=mod_r, fname=filename_right, exportType='STEP')

print(os.open(filename_right, os.O_RDONLY))



#dct_right_no_bottom = dactylutils.Dact().Config(show_caps = False)
#dct_left_no_bottom = dactylutils.Dact()



#base = baseplate(model_right())
#show_object(base)

#show_object(model_right())

#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.step"), exportType='STEP')
#cq.exporters.export(w=base, fname=path.join(r"..", "things", r"plate_og_py.dxf"), exportType='DXF')