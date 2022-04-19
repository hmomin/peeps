import bpy
import numpy as np
import sys

# change these directories to...
# ...where you want the LaTeX SVGs to be stored and where you'll store your own
# custom SVGs
SVG_DIR = "C:/Users/momin/Documents/_Blender/blends/svgs"
# ...where you want the output mini-videos to go
OUT_DIR = "C:/Users/momin/Documents/_Blender/blends/output"
# ...where you store external .blend files you would like to import objects from.
# you can create highly detailed objects in blender without painstakingly copying the
# console code, then just save the blend file and have the object ready to be imported
# at a moment's notice.
EXT_DIR = "C:/Users/momin/Documents/_Blender/blends/external_blends"
for direc in [SVG_DIR, OUT_DIR, EXT_DIR]:
    if direc not in sys.path:
        sys.path.append(direc)

C = bpy.context
D = bpy.data
ev = C.scene.eevee
FRAME_RATE = 60  # FPS
dt = 1 / FRAME_RATE
# render samples
ev.taa_render_samples = 64
# set bloom off
ev.use_bloom = False
# color map
WHITE = (1, 1, 1, 1)
CYAN = (0, 1, 1, 1)
MAGENTA = (1, 0, 1, 1)
YELLOW = (1, 1, 0, 1)
RED = (1, 0, 0, 1)
GREEN = (0, 1, 0, 1)
BLUE = (0, 0, 1, 1)
BLACK = (0, 0, 0, 1)
GRAY = (0.05, 0.05, 0.05, 1)
LIGHT_GRAY = (0.1, 0.1, 0.1, 1)
WHITE_GRAY = (0.5, 0.5, 0.5, 1)
SANDY_BROWN = (0.905, 0.371, 0.117, 1)
CHOCOLATE = (0.644, 0.141, 0.013, 1)
ORANGE = (1, 0.319, 0, 1)
OCEAN = (0.068, 0.434, 0.305, 1.0)
SNOW_WHITE = (0.905, 0.913, 0.761, 1.0)
DARK_KHAKI = (0.509, 0.474, 0.147, 1.0)
LEMON = (0.863, 0.982, 0.114, 1.0)
HONEY = (1.000, 0.546, 0.003, 1.0)
SADDLE_BROWN = (0.258, 0.060, 0.007, 1)
PURPLE = (0.216, 0, 0.216, 1)
PINK = (1, 0.527, 0.597, 1)
BROWN = (0.130, 0.056, 0.015, 1)
SILVER = (0.527, 0.527, 0.527, 1)
GOLD = (1, 0.68, 0, 1)
COPPER = (0.479, 0.171, 0.033, 1)
ZINC = SILVER
GLASS = (0.319, 0.591, 0.604, 1)
LIGHT_GREEN = (0, 1, 0.216, 1)
# bright colorblind-friendly palette
A1 = (0.716, 0.019, 0.212, 1)
A2 = (0.991, 0.120, 0.000, 1)
A3 = (1.000, 0.434, 0.000, 1)
A4 = (0.202, 0.738, 0.147, 1)
A5 = (0.091, 0.905, 0.973, 1)
A6 = (0.127, 0.275, 1.000, 1)
A7 = (0.188, 0.122, 0.871, 1)
# axes
X = (1, 0, 0)
Y = (0, 1, 0)
Z = (0, 0, 1)
ORIGIN = (0, 0, 0)
# bezier inputs (exactly as in CSS animations)
LINEAR = (0, 0, 1, 1)
EASE = (0.25, 0.1, 0.25, 1)
EASE_IN = (0.42, 0, 1, 1)
EASE_IN_OUT = (0.42, 0, 0.58, 1)
EASE_OUT = (0, 0, 0.58, 1)
# more bezier inputs for smooth, perceivably linear fading to/from black
MAKE_LIGHT = (1, 0, 1, 1)
MAKE_DARK = (0, 1, 1, 1)
# other constants
PI = np.pi
TAU = 2 * PI
GOLDEN_RATIO = (np.sqrt(5) + 1) / 2
GOLDEN_ANGLE = (2 - GOLDEN_RATIO) * TAU
G_ACCEL = 9.8  # m/s^2
G_CONST = 6.67428 * 10 ** (-11)  # m^3/(kg*s^2)
MU_KNOT = 4 * PI * 10 ** (-7)  # T*m/A
LIGHT_SPEED = 2.99792458 * 10 ** (8)  # m/s
EPS_KNOT = 1 / (MU_KNOT * LIGHT_SPEED ** 2)  # C^2/(N*m^2)
K_COULOMB = 8.987551788 * 10 ** (9)  # N*m^2/C^2
MASS_PROTON = 1.672621637 * 10 ** (-27)  # kg
MASS_NEUTRON = 1.674927211 * 10 ** (-27)  # kg
MASS_ELECTRON = 9.10938215 * 10 ** (-31)  # kg
ELEM_CHARGE = 1.602176487 * 10 ** (-19)  # C
EV_PER_JOULE = 1.602176487 * 10 ** (-19)  # eV/J
JOULE_PER_EV = 1 / EV_PER_JOULE  # J/eV
# tex template
TEMPLATE_TEX_FILE_BODY = r"\documentclass[preview]{standalone}\usepackage[siunitx, RPvoltages]{circuitikz}\usepackage[utf8]{inputenc}\usepackage{textcomp}\usepackage{esvect}\usepackage[english]{babel}\usepackage{amsmath}\usepackage{amssymb}\usepackage{textgreek}\usepackage{upgreek}\usepackage{dsfont}\usepackage{setspace}\usepackage{tipa}\usepackage{relsize}\usepackage{textcomp}\usepackage{mathrsfs}\usepackage{calligra}\usepackage{wasysym}\usepackage{ragged2e}\usepackage{physics}\usepackage{xcolor}\usepackage{microtype}\usepackage{pgfplots}\usepackage{circuitikz}\usepackage{tikz}\usetikzlibrary{shapes,arrows,automata,positioning,decorations.pathmorphing}\usetikzlibrary{arrows,shapes,trees}\usetikzlibrary{intersections}\usetikzlibrary{calc}\usetikzlibrary{automata}\usetikzlibrary{calendar}\usetikzlibrary{er}\usetikzlibrary{matrix}\usetikzlibrary{folding}\usetikzlibrary{patterns}\usetikzlibrary{plothandlers}\usetikzlibrary{shapes}\usetikzlibrary{plotmarks}\usetikzlibrary{snakes}\usetikzlibrary{topaths}\usetikzlibrary{babel}\usetikzlibrary{shadings}\DisableLigatures{encoding = *, family = * }\linespread{1}\begin{document}\begin{align*}YOUR_TEXT_HERE\end{align*}\end{document}"
# svg scaling for sizes of different files - each svg is normalized to a length of 4
SVG_SCALING = {
    "hand_poke": 37,
    "hand_hold": 26,
    "hand_stop": 33,
    "sizzle": 8,
    "speech_bubble": 66,
    "cloud": 15,
}
# initiate limitless counter of all objects (dead or alive)
OBJECT_COUNTER = 0

class CustomError(Exception):
    # just a simple way to distinguish between python-specific errors and personal errors
    pass