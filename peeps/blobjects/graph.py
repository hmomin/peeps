import bpy # pylint: disable=import-error
import math
import mathutils as mut
import numpy as np
from collections import deque
from constants import Z, CustomError, D, C, X, Y, ORIGIN, TAU, PI, EASE_IN_OUT,\
    WHITE, BLACK, OCEAN, FRAME_RATE
from blobjects.blobject import Blobject
from blobjects.shapes import Ball, Curve, Cylinder, Vector
from blobjects.text import Tex
from externals.blender_utils import selectOnly, delete
from externals.bezier_interpolation import interpolate
from externals.iterable_utils import flattenOnce, addition, mag

class Axis(Blobject):
    def __init__(
        self,
        axis=Z,
        thickness=0.02,
        length=10.5,
        tickInterval=1,
        tickHeight=0.5,
        ticksOn=True,
        labelsOn=True,
        labelOn=True,
        labelInterval=1,
        axisLabel="",
    ):
        """Constructor for Axis to be used in a graph.

        Args:
            axis (tuple, optional): A 3-tuple that defines the axis direction.
                Defaults to Z.
            thickness (float, optional): Thickness of axis. Defaults to 0.02.
            length (float, optional): Total length of axis. Defaults to 10.5.
            tickInterval (int, optional): Interval of tick-marks on axis. Defaults
                to 1.
            tickHeight (float, optional): Height of tick-marks. Defaults to 0.5.
            ticksOn (bool, optional): Determines whether you want axis tick marks
                to show on the axis. Defaults to True.
            labelsOn (bool, optional): Determines whether or not you want tick
                labels to show up (0, 1, 2, 3, ...). Defaults to True.
            labelOn (bool, optional): Determines whether or not you want an axis
                label to show up (x, y, z, ...). Defaults to True.
            labelInterval (float, optional): Determines the distance between ticks.
                Defaults to 1.
            axisLabel (str, optional): The label given to the entire axis. Defaults
                to "x" if axis in x-direction, "y" if axis in y-direction, or "z"
                if axis in z-direction.

        Raises:
            CustomError: labelInterval must be a constant multiple of tickInterval.
            CustomError: Axis length must be greater than 0. Rotate it if you need
                it in another direction.
            CustomError: Axis thickness must be greater than 0.
            CustomError: tickInterval can't be bigger than axis length.
            CustomError: Only x, y, z axes currently supported by Axis().
        """
        super().__init__()
        self.texNames = []
        # error checking for poor values
        checker = labelInterval / tickInterval
        if checker != math.floor(checker):
            raise CustomError(
                "labelInterval must be a constant multiple of tickInterval"
            )
        if length <= 0:
            raise CustomError(
                "Axis length must be greater than 0. Rotate it if you need it in the other direction"
            )
        if thickness <= 0:
            raise CustomError("Axis thickness must be greater than 0")
        if tickInterval > length:
            raise CustomError("tickInterval can't be bigger than the length")
        if axis != (1, 0, 0) and axis != (0, 1, 0) and axis != (0, 0, 1):
            raise CustomError("Only x, y, z axes currently supported by Axis(Blobject)")
        self.v = Vector(0, 0, length, thickness=thickness)
        currObj = D.objects[self.v.name[0]]
        # create ticks out of cylinders
        if ticksOn:
            tick = 0
            while tick < length - 0.5:
                if tick == 0:
                    tick += tickInterval
                    continue
                c = Cylinder(radius=thickness, height=tickHeight, origin=(0, 0, tick))
                c.rotate(X, 90, True)
                tick += tickInterval
                # fuse cylinder to axis
                selectOnly([self.v.name[0], c.name[0]])
                C.view_layer.objects.active = D.objects[self.v.name[0]]
                # now, join them
                bpy.ops.object.join()
                currObj = D.objects[self.v.name[0]]
        self.id = self.createID("axis")
        strI = self.stringID(self.id)
        # change name
        self.name = ["axis" + strI]
        currObj.name = self.name[0]
        C.scene.cursor.location = ORIGIN
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        if axis == Y:
            self.rotate(Z, TAU / 4)
            self.rotate(X, 3 * TAU / 4)
            self.normal = (0, 1, 0)
        elif axis == X:
            self.rotate(Y, TAU / 4)
            self.normal = (1, 0, 0)
        # now create the tick labels, dependent on x, y, z placement
        if ticksOn and labelsOn:
            labelPlacement = 0
            while labelPlacement < length - 0.5:
                if labelPlacement == 0:
                    labelPlacement += labelInterval
                    continue
                t = Tex("\\text{" + str(labelPlacement) + "}", scale=0.2)
                for name in t.name:
                    C.view_layer.objects.active = D.objects[name]
                    bpy.ops.object.constraint_add(type="CHILD_OF")
                    C.object.constraints["Child Of"].target = D.objects[self.name[0]]
                    self.texNames.append(name)
                # place labels in correct spot
                if axis == X:
                    t.shift(labelPlacement, -(tickHeight / 2 + 0.5), 0)
                    t.rotate(Y, 3 * TAU / 4)
                elif axis == Y:
                    t.shift(-(tickHeight / 2 + 0.5), labelPlacement, 0)
                    t.normal = Y
                    t.rotate(X, TAU / 4)
                    t.rotate(Z, 3 * TAU / 4)
                elif axis == Z:
                    t.normal = Z
                    t.shift(0, -(tickHeight / 2 + 0.5), labelPlacement)
                    t.transform(X)
                    t.rotate(X, TAU / 4)
                labelPlacement += labelInterval
        # now rename axis labels
        if labelOn:
            if axis == X:
                axisLabel = "x" if axisLabel == "" else axisLabel
            elif axis == Y:
                axisLabel = "y" if axisLabel == "" else axisLabel
            elif axis == Z:
                axisLabel = "z" if axisLabel == "" else axisLabel
            t = Tex(axisLabel, scale=0.4)
            self.mainLabel = t
            for name in t.name:
                C.view_layer.objects.active = D.objects[name]
                bpy.ops.object.constraint_add(type="CHILD_OF")
                C.object.constraints["Child Of"].target = D.objects[self.name[0]]
                self.texNames.append(name)
            if axis == X:
                t.shift(length + 0.5, -(tickHeight / 2 + 0.5), 0)
                t.rotate(Y, 3 * TAU / 4)
            elif axis == Y:
                t.shift(-(tickHeight / 2 + 0.5), length + 0.5, 0)
                t.normal = Y
                t.rotate(X, TAU / 4)
                t.rotate(Z, 3 * TAU / 4)
            elif axis == Z:
                t.normal = Z
                t.shift(0, -(tickHeight / 2 + 0.5), length + 0.5)
                t.transform(X)
                t.rotate(X, TAU / 4)

    # regular rotate labels
    def rotateLabels(self, axis=Y, angle=PI / 2):
        """Rotates the labels of the axis.

        Args:
            axis (tuple, optional): 3-tuple that defines rotation axis. Defaults to Y.
            angle (float, optional): Rotation angle in radians. Defaults to PI/2.
        """
        for name in self.texNames:
            selectOnly([name])
            obj = D.objects[name]
            # determine quaternion
            q = mut.Quaternion(axis, angle)
            q.normalize()
            # perform quaternion rotation
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = q @ obj.rotation_quaternion
    def init_rotateLabels(self, t0=0, tf=1, rate=EASE_IN_OUT, axis=Y, angle=PI / 2):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling init_rotate() requires a new non-zero axis to be passed in as newNormal"
            )
        t = interpolate(t0, tf, rate)
        t.pop(0)
        diffs = np.diff(interpolate(0, angle, rate, numIntervals=len(t))).tolist()
        stack = deque()
        diffs.reverse()
        for smallAngle in diffs:
            stack.append(smallAngle)
        return stack
    def update_rotateLabels(self, val, axis=Y, angle=PI / 2):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.rotateLabels(axis, val)

    # only used to get around indeterminate quaternion rotations
    def flipLabels(self, axis=Y, angle=PI / 2):
        """Flips the labels about some axis by using a half-angle.

        Args:
            axis (tuple, optional): 3-tuple that defines axis of rotation. Defaults
                to Y.
            angle (float, optional): Half-angle through which to rotate. Probably
                best not to pass this in, since it defaults to PI/2.
        """
        for name in self.texNames:
            selectOnly([name])
            obj = D.objects[name]
            # determine quaternion
            q = mut.Quaternion(axis, angle)
            q.normalize()
            q2 = mut.Quaternion(axis, angle)
            q2.normalize()
            # perform quaternion rotation
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = q @ q2 @ obj.rotation_quaternion
    def init_flipLabels(self, t0=0, tf=1, rate=EASE_IN_OUT, axis=Y, angle=PI / 2):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling init_rotate() requires a new non-zero axis to be passed in as newNormal"
            )
        t = interpolate(t0, tf, rate)
        t.pop(0)
        diffs = np.diff(interpolate(0, angle, rate, numIntervals=len(t))).tolist()
        stack = deque()
        diffs.reverse()
        for smallAngle in diffs:
            stack.append(smallAngle)
        return stack
    def update_flipLabels(self, val, axis=Y, angle=PI / 2):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.flipLabels(axis, val)

class Graph2D(Blobject):
    def __init__(
        self,
        axesThickness=0.05,
        axesLength=10,
        ticksOn=True,
        labelsOn=True,
        labelOn=True,
        negativeOn=True,
    ):
        """
        This is mostly here for backwards compatibility purposes - I recommend
        GraphFlexible() for a lot more options and flexibility. This creates a
        2D graph out of Axis() objects.

        Args:
            axesThickness (float, optional): thickness of each axis. Defaults to 0.05.
            axesLength (float, optional): length of each axis. Defaults to 10.
            ticksOn (bool, optional): determines whether or not ticks show up on
                axes. Defaults to True.
            labelsOn (bool, optional): determines whether or not labels show up at
                tick marks on axes. Defaults to True.
            labelOn (bool, optional): determines whether or not axis labels (x, y, z)
                show up on axes. Defaults to True.
            negativeOn (bool, optional): determines whether or not the axes extend in
                the negative direction or not. Defaults to True.
        """
        super().__init__()
        self.assets = []
        # assets in clockwise order (right, up, left, down)
        self.assets.append(
            Axis(
                X,
                axesThickness,
                axesLength,
                ticksOn=ticksOn,
                labelsOn=labelsOn,
                labelOn=labelOn,
            )
        )
        self.assets.append(
            Axis(
                Y,
                axesThickness,
                axesLength,
                ticksOn=ticksOn,
                labelsOn=labelsOn,
                labelOn=labelOn,
            )
        )
        if negativeOn:
            self.assets.append(
                Axis(
                    X,
                    axesThickness,
                    axesLength,
                    ticksOn=ticksOn,
                    labelsOn=labelsOn,
                    labelOn=False,
                )
            )
            self.assets[-1].rotate(angle=PI)
            self.assets.append(
                Axis(
                    Y,
                    axesThickness,
                    axesLength,
                    ticksOn=ticksOn,
                    labelsOn=labelsOn,
                    labelOn=False,
                )
            )
            self.assets[-1].rotate(angle=PI)
        self.name = flattenOnce([asset.name for asset in self.assets])
        self.texNames = flattenOnce([asset.texNames for asset in self.assets])

    def rotate(self, axis=(0, 0, 1), angle=0, angleDeg=False):
        """Rotates the entire graph about its origin.

        Args:
            axis (tuple, optional): axis of rotation. Defaults to (0, 0, 1).
            angle (float, optional): rotation angle. Defaults to 0.
            angleDeg (bool, optional): whether or not angle is in degrees. Defaults
                to False, i.e. radians.

        Raises:
            CustomError: non-zero rotation axis required
            CustomError: can't rotate the graph by a 180 degree rotation, because of
                quaternion indeterminacy. Use two 90 degree rotations instead.
        """
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a reasonable rotation axis to be passed in as a tuple"
            )
        if angleDeg:
            angle = angle * PI / 180
        # determine quaternion
        q = mut.Quaternion(axis, angle)
        # check for indeterminacy of q
        if q.magnitude == 0:
            raise CustomError(
                "Indeterminate Quaternion Rotation: make use of another rotation to interpolate between antiparallel states"
            )
        q.normalize()
        selectOnly(self.name)
        i = -1
        for name in self.name:
            i += 1
            obj = D.objects[name]
            # perform quaternion rotation
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = q @ obj.rotation_quaternion
        # reset normal
        oldVec = mut.Vector(self.normal)
        newVec = q @ oldVec
        self.normal = newVec[:]
    def init_rotate(
        self, t0=0, tf=1, rate=EASE_IN_OUT, axis=(0, 0, 1), angle=0, angleDeg=False
    ):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling init_rotate() requires a new non-zero axis to be passed in as newNormal"
            )
        t = interpolate(t0, tf, rate)
        t.pop(0)
        diffs = np.diff(interpolate(0, angle, rate, numIntervals=len(t))).tolist()
        stack = deque()
        diffs.reverse()
        for smallAngle in diffs:
            stack.append(smallAngle)
        return stack
    def update_rotate(self, val, axis=(0, 0, 1), angle=0, angleDeg=False):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.rotate(axis, val, angleDeg)

    def shift(self, x=0, y=0, z=0):
        """Shifts the graph.

        Args:
            x (float, optional): x-shift of graph. Defaults to 0.
            y (float, optional): y-shift of graph. Defaults to 0.
            z (float, optional): z-shift of graph. Defaults to 0.
        """
        for ax in self.assets:
            ax.shift(x, y, z)
    def init_shift(self, t0=0, tf=1, rate=EASE_IN_OUT, x=0, y=0, z=0):
        return super().init_shift(t0, tf, rate, x, y, z)
    def update_shift(self, val, x=0, y=0, z=0):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        for ax in self.assets:
            ax.shift(*val)

    def color(self, theColor=WHITE):
        """Colors the components in the graph

        Args:
            theColor (tuple, optional): 4-tuple that defines the color.
                Defaults to WHITE.
        """
        for ax in self.assets:
            ax.color(theColor)
    def init_color(self, t0=0, tf=1, rate=EASE_IN_OUT, theColor=WHITE):
        return super().init_color(t0, tf, rate, theColor)
    def update_color(self, val, theColor=WHITE):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        for ax in self.assets:
            ax.color(val)

    def delete(self):
        """
        Deletes the graph.
        """
        for ax in self.assets:
            ax.delete()

class GraphFlexible(Blobject):
    def __init__(
        self,
        xLabel="t",
        yLabel="f(t)",
        xLabelShift=[0, 0, 0],
        yLabelShift=[0, 0, 0],
        origin=(-10, -8, 0),
        xAxisLength=24,
        yAxisLength=15,
        axisThickness=0.05,
        labelScale=0.7,
    ):
        """Basically a Graph2D(), but with a lot more flexibility in creation.

        Args:
            xLabel (str, optional): label of the x-axis. Defaults to "t".
            yLabel (str, optional): label of the y-axis. Defaults to "f(t)".
            xLabelShift (list, optional): relative shift of the x-axis label. A good
                idea might be to leave it at [0, 0, 0] at first and then tweak it from
                there with reference to the UI. Defaults to [0, 0, 0].
            yLabelShift (list, optional): relative shift of the y-axis label. A good
                idea might be to leave it at [0, 0, 0] at first and then tweak it from
                there with reference to the UI. Defaults to [0, 0, 0].
            origin (tuple, optional): where the origin of the graph ends up. Defaults
                to (-10, -8, 0).
            xAxisLength (float, optional): length of x-axis. Defaults to 24.
            yAxisLength (float, optional): length of y-axis. Defaults to 15.
            axisThickness (float, optional): thickness of each axis. Defaults to 0.05.
            labelScale (float, optional): scale of labels. Defaults to 0.7.
        """
        super().__init__()
        self.origin = origin
        self.xAxis = Vector(xAxisLength, 0, 0, origin, BLACK, axisThickness)
        xTip = addition(origin, (xAxisLength, 0, 0))
        self.xLabel = Tex(xLabel, labelScale, False, addition(xTip, (3, -2, 0)))
        self.xLabel.shift(*xLabelShift)
        self.yAxis = Vector(0, yAxisLength, 0, origin, BLACK, axisThickness)
        yTip = addition(origin, (0, yAxisLength, 0))
        self.yLabel = Tex(yLabel, labelScale, False, addition(yTip, (-5, -1, 0)))
        self.yLabel.shift(*yLabelShift)
        self.curve = None
        self.name = [
            name
            for name in [
                *self.xAxis.name,
                *self.xLabel.name,
                *self.yAxis.name,
                *self.yLabel.name,
            ]
        ]

    def draw(
        self, f, func=lambda t: t, runtime=5, xTruncate=2, yTruncate=2, curveColor=OCEAN
    ):
        """Draws out the graph as a render if f.render.

        Args:
            f (Frame): Frame object to be used in rendering.
            func (function, optional): function to draw out on the graph. Defaults
                to lambda t: t.
            runtime (float, optional): runtime of the animation. Defaults to 5.
            xTruncate (float, optional): determines the x-limit of the graphed
                function. Defaults to 2.
            yTruncate (float, optional): determines the y-limit of the graphed
                function. Defaults to 2.
            curveColor (tuple, optional): determines the color of graph. Defaults
                to OCEAN.
        """
        totalFrames = FRAME_RATE * runtime
        self.xWindow = mag(self.xAxis.normal) - xTruncate
        self.yWindow = mag(self.yAxis.normal) - yTruncate
        # dummy ball
        curve = Ball(1, (300, 0, 0))
        xDist = self.xWindow / totalFrames
        try:
            coords = [
                addition(self.origin, (-xDist, func(-xDist), 0)),
                addition(self.origin, (0, func(0), 0)),
                addition(self.origin, (xDist, func(xDist), 0)),
            ]
        except:
            coords = [
                addition(self.origin, (0, func(0), 0)),
                addition(self.origin, (xDist, func(xDist), 0)),
            ]
        currentX = 2 * xDist
        with f.video() as r:
            while (
                coords[-1][0] < self.origin[0] + self.xWindow
                and coords[-1][1] < self.origin[1] + self.yWindow
            ):
                coords.append(addition(self.origin, (currentX, func(currentX), 0)))
                # create the curve
                if f.render:
                    delete(curve)
                    curve = Curve(coords, curveColor, 0.1)
                r()
                currentX += xDist
        if not f.render:
            delete(curve)
            curve = Curve(coords, curveColor, 0.1)
        self.curve = curve

class GraphSpace(Blobject):
    def __init__(
        self,
        axesThickness=0.05,
        axesLength=10,
        ticksOn=True,
        labelsOn=True,
        gridOn=False,
        mainLabels=True,
    ):
        """Creates a 3D-graph (what I call a GraphSpace).

        Args:
            axesThickness (float, optional): determines the thicknesses of the axes.
                Defaults to 0.05.
            axesLength (float, optional): determines the length of the axes. Defaults
                to 10.
            ticksOn (bool, optional): determines whether or not tick marks show up on
                the axes. Defaults to True.
            labelsOn (bool, optional): determines whether or not labels show up on the
                tick-marks. Defaults to True.
            gridOn (bool, optional): determines whether or not the grid lines show up
                in the x-y plane. Defaults to False.
            mainLabels (bool, optional): determines whether or not the main axis labels
                (x, y, z) show up on the graph. Defaults to True.
        """
        super().__init__()
        self.x = Axis(
            X,
            thickness=axesThickness,
            length=axesLength,
            ticksOn=ticksOn,
            labelsOn=labelsOn,
            labelOn=mainLabels,
        )
        self.y = Axis(
            Y,
            thickness=axesThickness,
            length=axesLength,
            ticksOn=ticksOn,
            labelsOn=labelsOn,
            labelOn=mainLabels,
        )
        self.z = Axis(
            Z,
            thickness=axesThickness,
            length=axesLength,
            ticksOn=ticksOn,
            labelsOn=labelsOn,
            labelOn=mainLabels,
        )
        self.gridLines = []
        if gridOn:
            for i in range(-axesLength + 2, axesLength - 1):
                self.gridLines.append(Cylinder(0.01, 2 * (axesLength - 1), (i, 0, 0)))
                self.gridLines[-1].rotate(X, PI / 2)
            for j in range(-axesLength + 2, axesLength - 1):
                self.gridLines.append(Cylinder(0.01, 2 * (axesLength - 1), (0, j, 0)))
                self.gridLines[-1].rotate(Y, PI / 2)
        self.name = flattenOnce([self.x.name, self.y.name, self.z.name])
        self.texNames = flattenOnce([self.x.texNames, self.y.texNames, self.z.texNames])

    def rotate(self, axis=ORIGIN, angle=0, angleDeg=False):
        """Rotates the GraphSpace about some axis by some angle.

        Args:
            axis (tuple, optional): 3-tuple axis of rotation. Defaults to ORIGIN.
            angle (int, optional): angle of rotation. Defaults to 0.
            angleDeg (bool, optional): whether or not the angle is in degrees.
                Defaults to False, so the angle is expected in radians.
        """
        for ax in [self.x, self.y, self.z]:
            ax.rotate(axis, angle, angleDeg)
        for gridLine in self.gridLines:
            gridLine.rotate(axis, angle, angleDeg)
    def init_rotate(
        self, t0=0, tf=1, rate=EASE_IN_OUT, axis=ORIGIN, angle=0, angleDeg=False
    ):
        return super().init_rotate(t0, tf, rate, axis, angle, angleDeg)
    def update_rotate(self, val, axis=ORIGIN, angle=0, angleDeg=False):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        for ax in [self.x, self.y, self.z]:
            ax.rotate(axis, val, angleDeg)
        for gridLine in self.gridLines:
            gridLine.rotate(axis, val, angleDeg)

    def shift(self, x=0, y=0, z=0):
        """Shifts the GraphSpace

        Args:
            x (float, optional): x-shift of the GraphSpace. Defaults to 0.
            y (float, optional): y-shift of the GraphSpace. Defaults to 0.
            z (float, optional): z-shift of the GraphSpace. Defaults to 0.
        """
        for ax in [self.x, self.y, self.z]:
            ax.shift(x, y, z)
        for gridLine in self.gridLines:
            gridLine.shift(x, y, z)
    def init_shift(self, t0=0, tf=1, rate=EASE_IN_OUT, x=0, y=0, z=0):
        return super().init_shift(t0, tf, rate, x, y, z)
    def update_shift(self, val, x=0, y=0, z=0):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        for ax in [self.x, self.y, self.z]:
            ax.shift(*val)
        for gridLine in self.gridLines:
            gridLine.shift(*val)

    def color(self, theColor=WHITE, gridRatio=0.05):
        """Colors the GraphSpace.

        Args:
            theColor (tuple, optional): 4-tuple that defines the color of the
                GraphSpace. Defaults to WHITE.
            gridRatio (float, optional): the coloring ratio of the grid-lines.
                You don't necessarily want the color of the grid-lines to be exactly
                the same as the color of the axes (a ratio of 1.0), but you also don't
                want the grid-line colors to be nonexistent (a ratio of 0). Defaults
                to 0.05.
        """
        for ax in [self.x, self.y, self.z]:
            ax.color(theColor)
        gridColor = [i * gridRatio for i in theColor]
        gridColor[3] = 1
        gridColor = tuple(gridColor)
        for gridline in self.gridLines:
            gridline.color(gridColor)
    def init_color(self, t0=0, tf=1, rate=EASE_IN_OUT, theColor=WHITE, gridRatio=0.05):
        return super().init_color(t0, tf, rate, theColor)
    def update_color(self, val, theColor=WHITE, gridRatio=0.05):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.color(val, gridRatio)

    def delete(self):
        """
        Deletes the GraphSpace.
        """
        for ax in [self.x, self.y, self.z]:
            ax.delete()
        for gridLine in self.gridLines:
            gridLine.delete()
