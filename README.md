# dactyl_manuform_keyboard_generator_Python

This is a fork of the Dactyl Manuform keyboard generator by joshreve: https://github.com/joshreve/dactyl-keyboard
This code should be slightly more organized and easier to use. In progress

# Status

![](renders/status.png)

# How to use

Tested with Python 3.8 and 3.9

Install the necesary packages. 
Run Python dactcreate.py This will generate a bunch of step files in /Things

Modify dactcreate.py to your liking to get to the exact keyboard STEP file that you want. 

Modify these lines to configure your keyboard. 
conf1 = dactylutils.Dact.Config(show_caps   = True,
                                script_print_shapes = True,
                                 nrows      = 5,
                                 ncols      = 6,
                                 )

You can find more configuration options under the Config @dataclass in the dactultils.py file. 

GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007