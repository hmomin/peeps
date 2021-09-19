import importlib

import dynamics.electricity
import dynamics.field_lines
import dynamics.gravity

importlib.reload(dynamics.electricity)
importlib.reload(dynamics.field_lines)
importlib.reload(dynamics.gravity)

from dynamics.electricity import *
from dynamics.field_lines import *
from dynamics.gravity import *