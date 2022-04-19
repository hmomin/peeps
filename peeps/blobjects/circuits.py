import bpy
import numpy as np
from constants import ORIGIN, WHITE, CustomError
from blobjects.blobject import Blobject
from blobjects.shapes import Cylinder, NodeWires, Line
from blobjects.text import Tex
from externals.blender_utils import selectOnly
from externals.iterable_utils import addition, flattenOnce, multiply
from externals.miscellaneous import computeAbsoluteNodes

class Ammeter(Blobject):
    def __init__(self, scale=1, origin=ORIGIN):
        """Constructor for Ammeter.

        Args:
            scale (int, optional): Scale size of ammeter. Defaults to 1.
            origin ([type], optional): Origin of ammeter. Defaults to ORIGIN.
        """
        super().__init__()
        # fix poor input
        scale = np.abs(scale)
        self.scale = scale
        self.origin = origin
        self.body = Cylinder(scale, 0.01, origin)
        self.tex = Tex("\\text{A}", scale / 3, False, addition(origin, (0, 0, 0.1)))
        self.components = [self.body, self.tex]
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*origin)
        self.name = flattenOnce([component.name for component in self.components])

    def color(self, theColor=WHITE, ignoreTampered=False):
        self.body.color(theColor, ignoreTampered)

    def changeLabel(self, expression, scale=-1):
        """
        Allows the label of the ammeter to change from 'A' to something else.

        Args:
            expression (str): Latex expression for new label.
            scale (int, optional): Scale of new label. Defaults to -1.
        """
        if scale == -1:
            scale = self.tex.scale
        self.tex.delete()
        self.tex = Tex(
            expression, scale, self.tex.twistable, addition(self.origin, (0, 0, 0.1))
        )
        self.components = [self.body, self.tex]
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*self.origin)
        self.name = flattenOnce([component.name for component in self.components])

class Battery(Blobject):
    def __init__(self, scale=1, origin=ORIGIN, ends=True, plusMinus=True):
        """
        A simple battery as in a circuit schematic, with a long end for the
        positive terminal and a short end for the negative terminal.

        Args:
            scale (float, optional): Size of the battery. Defaults to 1.
            origin (tuple, optional): 3-tuple that defines origin. Defaults to
                ORIGIN.
            ends (bool, optional): Determines whether or not to show ends sticking
                off of the battery terminals. Defaults to True.
            plusMinus (bool, optional): Determines whether or not to show + or -
                values on the ends of the battery. Defaults to True.

        Raises:
            CustomError: scale must be greater than 0
        """
        super().__init__()
        # error-checking on poor inputs
        if scale <= 0:
            raise CustomError("scale must be greater than 0")
        self.scale = scale
        self.origin = origin
        self.components = []
        self.components.append(
            Line(
                addition(origin, (-0.5, -1.5, 0)), addition(origin, (-0.5, 1.5, 0)), 0.1
            )
        )
        self.components.append(
            Line(addition(origin, (0.5, -0.5, 0)), addition(origin, (0.5, 0.5, 0)), 0.1)
        )
        if ends:
            self.left = addition(origin, (-2.5 * scale, 0, 0))
            self.right = addition(origin, (+2.5 * scale, 0, 0))
            self.components.append(
                Line(
                    addition(origin, (-0.5, 0, 0)), addition(origin, (-2.5, 0, 0)), 0.1
                )
            )
            self.components.append(
                Line(
                    addition(origin, (+0.5, 0, 0)), addition(origin, (+2.5, 0, 0)), 0.1
                )
            )
        else:
            self.left = addition(origin, (-0.5 * scale, 0, 0))
            self.right = addition(origin, (+0.5 * scale, 0, 0))
        # add the plus/minus
        if plusMinus:
            self.components.append(
                Line(
                    addition(origin, (-1.2, 0.7, 0)),
                    addition(origin, (-1.2, 1.3, 0)),
                    0.02,
                )
            )
            self.components.append(
                Line(
                    addition(origin, (-0.9, 1, 0)), addition(origin, (-1.5, 1, 0)), 0.02
                )
            )
            self.components.append(
                Line(
                    addition(origin, (+0.9, 0.5, 0)),
                    addition(origin, (+1.4, 0.5, 0)),
                    0.02,
                )
            )
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*origin)
        self.name = flattenOnce([component.name for component in self.components])
        # rescale to scale
        selectOnly(self.name)
        bpy.ops.transform.resize(value=(scale, scale, scale), mirror=True)

    def color(self, theColor=WHITE, ignoreTampered=False):
        """
        Colors the battery a certain color.

        Args:
            theColor (tuple, optional): 4-tuple (R, G, B, 1) that defines the color
                to make the battery. Defaults to WHITE.
            ignoreTampered (bool, optional): Probably a good idea to just leave this
                as False. It's needed when there are Tex objects that have been
                rendered in without being flipped (see Tex.morphFrom()). Defaults
                to False.
        """
        super().color(theColor, ignoreTampered)
        for component in self.components:
            component.objColor = self.objColor

class Capacitor(Blobject):
    def __init__(self, scale=1, origin=ORIGIN, ends=True):
        """A simple capacitor as in a circuit schematic.

        Args:
            scale (float, optional): Scale of capacitor. Defaults to 1.
            origin (tuple, optional): Origin of capacitor. Defaults to ORIGIN.
            ends (bool, optional): Determines whether or not ends should be shown.
                Defaults to True.

        Raises:
            CustomError: scale must be greater than 0
        """
        super().__init__()
        # error-checking on poor inputs
        if scale <= 0:
            raise CustomError("scale must be greater than 0")
        self.scale = scale
        self.origin = origin
        self.components = []
        self.components.append(
            Line(addition(origin, (-0.5, -1, 0)), addition(origin, (-0.5, 1, 0)), 0.1)
        )
        self.components.append(
            Line(addition(origin, (0.5, -1, 0)), addition(origin, (0.5, 1, 0)), 0.1)
        )
        if ends:
            self.left = addition(origin, (-2.5, 0, 0))
            self.right = addition(origin, (+2.5, 0, 0))
            self.components.append(Line(addition(origin, (-0.5, 0, 0)), self.left, 0.1))
            self.components.append(
                Line(addition(origin, (+0.5, 0, 0)), self.right, 0.1)
            )
        else:
            self.left = addition(origin, (-0.5, 0, 0))
            self.right = addition(origin, (+0.5, 0, 0))
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*origin)
        self.name = flattenOnce([component.name for component in self.components])
        # rescale to scale
        selectOnly(self.name)
        bpy.ops.transform.resize(value=(scale, scale, scale), mirror=True)
        self.left = (self.left[0] * scale, self.left[1], self.left[2])
        self.right = (self.right[0] * scale, self.right[1], self.right[2])

    def color(self, theColor=WHITE, ignoreTampered=False):
        """Colors capacitor.

        Args:
            theColor (tuple, optional): 4-tuple (R, G, B, 1) that determines color
                of capacitor. Defaults to WHITE.
            ignoreTampered (bool, optional): Probably best to leave this as False.
                Related to Tex.morphFrom(), but not really. Defaults to False.
        """
        super().color(theColor, ignoreTampered)
        for component in self.components:
            component.objColor = self.objColor

class Resistor(NodeWires):
    def __init__(self, scale=1, origin=ORIGIN, ends=True):
        """A simple resistor schematic as in a circuit diagram.

        Args:
            scale (float, optional): scale of Resistor. Defaults to 1.
            origin (tuple, optional): origin of Resistor. Defaults to ORIGIN.
            ends (bool, optional): determines whether or not ends show up on
                Resistor. Defaults to True.
        """
        # create nodes
        nodes = [
            (-2.5, 0, 0),
            (1, 0, 0),
            (0.25, -1, 0),
            (0.5, 2, 0),
            (0.5, -2, 0),
            (0.5, 2, 0),
            (0.5, -2, 0),
            (0.5, 2, 0),
            (0.25, -1, 0),
            (1, 0, 0),
        ]
        if not ends:
            nodes[0] = (-1.5, 0, 0)
            nodes.pop(1)
            nodes.pop()
        nodes = computeAbsoluteNodes(nodes)
        thickness = 0.1 * scale
        # adjust for scaling
        for i, n in enumerate(nodes):
            nodes[i] = multiply(scale, n)
        self.left = addition(nodes[0], origin)
        self.right = addition(nodes[-1], origin)
        self.nodes = nodes
        self.thickness = thickness
        super().__init__(nodes, thickness)
        self.shift(*origin)

class Voltmeter(Blobject):
    def __init__(self, scale=1, origin=ORIGIN):
        """Constructor for Voltmeter

        Args:
            scale (float, optional): scale of Voltmeter. Defaults to 1.
            origin (tuple, optional): origin of Voltmeter. Defaults to ORIGIN.
        """
        super().__init__()
        # fix poor input
        scale = np.abs(scale)
        self.scale = scale
        self.origin = origin
        self.body = Cylinder(scale, 0.01, origin)
        self.tex = Tex("\\text{V}", scale / 3, False, addition(origin, (0, 0, 0.1)))
        self.plus = Tex(
            "+", scale / 10, False, addition(origin, (-scale / 1.25, 0, 0.1))
        )
        self.minus = Tex(
            "-", scale / 10, False, addition(origin, (+scale / 1.25, 0, 0.1))
        )
        self.components = [self.body, self.tex, self.plus, self.minus]
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*origin)
        self.name = flattenOnce([component.name for component in self.components])

    def color(self, theColor=WHITE, ignoreTampered=False):
        """Colors the Voltmeter body without affecting the associated Tex.

        Args:
            theColor (tuple, optional): color of Voltmeter. Defaults to WHITE.
            ignoreTampered (bool, optional): needed for Tex morphing, but since
                that doesn't really apply here, it's probably best to leave this
                as False. Defaults to False.
        """
        self.body.color(theColor, ignoreTampered)

    def changeLabel(self, expression, scale=-1):
        """Allows the label of the Voltmeter to be changed to something else.

        Args:
            expression (str): Tex label for the Voltmeter.
            scale (float, optional): scale of new Tex. Defaults to -1.
        """
        if scale == -1:
            scale = self.tex.scale
        self.tex.delete()
        self.tex = Tex(
            expression, scale, self.tex.twistable, addition(self.origin, (0, 0, 0.1))
        )
        self.components = [self.body, self.tex, self.plus, self.minus]
        # make origin in the center
        for component in self.components:
            component.changeOriginTo(*self.origin)
        self.name = flattenOnce([component.name for component in self.components])
