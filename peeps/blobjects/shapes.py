import bpy
import bmesh
import mathutils as mut
import numpy as np
import os
import operator
import sys
from collections import deque
from statistics import mode, mean
from constants import ORIGIN, CustomError, PI, C, EASE_IN_OUT, BLACK, TAU, D,\
    ELEM_CHARGE, MASS_PROTON, WHITE, FRAME_RATE, LINEAR, SVG_SCALING, SVG_DIR
from blobjects.blobject import Blobject
from blobjects.text import Tex
from externals.bezier_interpolation import interpolate
from externals.blender_utils import selectOnly, computeQuaternion, delete
from externals.iterable_utils import difference, subtraction, mag, addition,\
    flattenOnce
from externals.miscellaneous import computeAbsoluteNodes

class NodeWires(Blobject):
    def __init__(
        self, nodes=[], thickness=0.1, color=BLACK, curvatureRadius=0.1, resolution=100
    ):
        """Constructor for NodeWires.

        Args:
            nodes (list, optional): List of nodes that define placement of wiring
                bends/junctions. If you want to go backwards, just use False as a
                node. Example:
                [
                    (5, 0, 0),
                    (0, 0, 0),
                    (0, 5, 0),
                    (5, 5, 0),
                    False,
                    (0, 10, 0),
                    (5, 10, 0)
                ]
                will trace out a capital E on the screen. Defaults to [].
            thickness (float, optional): Thickness of wiring. Defaults to 0.1.
            color ([type], optional): Color of wiring. Defaults to BLACK.
            curvatureRadius (float, optional): Curvature of nodes at bends.
                Definitely feel free to experiment with this. Defaults to 0.1.
            resolution (int, optional): How resolved the curvature at the bends is.
                I haven't noticed a drastic reduction in speed with too much
                resolution, but 100 seems to work well. Defaults to 100.

        Raises:
            CustomError: requires thickness > 0
            CustomError: requires len(nodes) > 1
            CustomError: no adjacent nodes may be antiparallel - if you need to go
                backwards, use False as specified above.
        """
        super().__init__()
        if thickness <= 0:
            raise CustomError("thickness must be greater than 0")
        if type(nodes) is not list or len(nodes) <= 1:
            raise CustomError("nodes must be a list of length 2 or greater")
        self.thickness = thickness
        # traverse the list until there are no more nodes left
        self.curveCoords = []
        self.components = []
        prevStack = []
        currCounter = 1
        backTrackStack = deque()
        prevStack.append(nodes[0])
        backTrackStack.append(nodes[0])
        while True:
            try:
                curr = nodes[currCounter]
            except IndexError:
                break
            if type(curr) is not tuple:
                if len(prevStack) != 0:
                    # give this stack to one of the curves
                    self.curveCoords.append(prevStack)
                    prevStack = []
                backTrackStack.pop()
            else:
                if len(prevStack) == 0:
                    prevStack.append(backTrackStack[-1])
                prevStack.append(curr)
                backTrackStack.append(curr)
            currCounter += 1
        self.curveCoords.append(prevStack)
        self.curves = []
        for i, coords in enumerate(self.curveCoords):
            curr = coords[0]
            modCoords = []
            for j, node in enumerate(coords):
                # determine the direction by taking into account the next node and previous node
                if j == 0:
                    prevNode = subtraction(
                        coords[j], subtraction(coords[j + 1], coords[j])
                    )
                else:
                    prevNode = coords[j - 1]
                try:
                    nextNode = coords[j + 1]
                except IndexError:
                    nextNode = subtraction(
                        coords[j], subtraction(coords[j - 1], coords[j])
                    )
                prevDirection = mut.Vector(subtraction(node, prevNode)).normalized()
                nextDirection = mut.Vector(subtraction(nextNode, node)).normalized()
                alpha = np.arccos(np.clip(prevDirection.dot(nextDirection), -1, 1))
                if alpha == PI:
                    # just break, idk what else to do
                    raise CustomError(
                        "NodeWire() error - nodes can't be antiparallel to each other"
                    )
                elif alpha > 0.001:
                    # move backwards to the starting point
                    r = curvatureRadius
                    s = r * np.tan(alpha / 2)
                    # move backwards a distance s
                    curr = addition(node, -s * prevDirection)
                    # determine the correct direction to go in
                    rotAxis = prevDirection.cross(nextDirection)
                    correctDirection = -prevDirection.cross(rotAxis)
                    # prevSpot = curr
                    circleOrigin = addition(curr, r * correctDirection)
                    # circleOrigin is now the origin of the curvature circle
                    # determine the angle between circleOrigin and the previous spot
                    pointer1 = -correctDirection
                    # we want to rotate pointer1 through an angle dalpha on each pointStep
                    dalpha = np.diff(interpolate(0, alpha, LINEAR, resolution))[0]
                    modCoords.append(addition(circleOrigin, tuple(r * pointer1)))
                    quat = mut.Quaternion(rotAxis, dalpha)
                    for _ in range(resolution):
                        pointer1 = quat @ pointer1
                        modCoords.append(addition(circleOrigin, tuple(r * pointer1)))
                else:
                    modCoords.append(addition(node, tuple(-0.001 * prevDirection)))
                    modCoords.append(node)
                    modCoords.append(addition(node, tuple(0.001 * nextDirection)))
            self.curves.append(Curve(modCoords, color, thickness))
            self.curveCoords[i] = modCoords
        self.name = flattenOnce([curve.name for curve in self.curves])

class Ball(Blobject):
    def __init__(self, radius=1, origin=ORIGIN, mass=-1):
        """Generates a ball with some radius at some origin.

        Args:
            radius (float, optional): Radius of Ball. Defaults to 1.
            origin (tuple, optional): 3-tuple that defines origin. Defaults to
                ORIGIN.
            mass (float, optional): Mass of Ball - needed for gravitational
                dynamics. Defaults to -1, in which case it simply becomes the
                volume of the ball.

        Raises:
            CustomError: radius must be greater than 0.
            CustomError: mass must be greater than 0.
        """
        super().__init__()
        # poor value checking
        if radius <= 0:
            raise CustomError("Ball radius must be greater than 0")
        if mass != -1 and mass <= 0:
            raise CustomError("Ball mass must be greater than 0")
        self.radius = radius
        self.origin = origin
        # check if mass wasn't passed in - use a density of 1
        if mass == -1:
            self.mass = 4 / 3 * PI * radius ** 3
        else:
            self.mass = mass
        self.id = self.createID("ball")
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=self.radius, segments=100, ring_count=100, location=self.origin
        )
        bpy.ops.object.shade_smooth()
        # determine name suffix for ball
        strI = self.stringID(self.id)
        self.name = ["ball" + strI]
        C.view_layer.objects.active.name = self.name[0]

    def change(self, radius=1, origin=ORIGIN):
        """
        Changes the ball from one (radius, origin) combination to another.
        """
        leColor = self.getColor()
        isTransparent = self.isTransparent
        leId = self.id
        self.delete()
        self.__init__(radius, origin, leId)
        self.color(leColor)
        if isTransparent:
            self.transparent(self.currentAlpha)
    def init_change(self, t0=0, tf=1, rate=EASE_IN_OUT, radius=1, origin=ORIGIN):
        # error checking
        if radius <= 0:
            raise CustomError("radius must be a non-zero positive value")
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # create a default linear scaling
        (x0, y0, z0) = self.origin
        (x1, y1, z1) = origin
        v1 = (radius - self.radius) / (tf - t0)
        v4 = (x1 - x0) / (tf - t0)
        v5 = (y1 - y0) / (tf - t0)
        v6 = (z1 - z0) / (tf - t0)
        og = [self.radius, x0, y0, z0]
        # define linear shifts
        def lam1(t):
            return og[0] + (t - t0) * v1

        def lam4(t):
            return og[1] + (t - t0) * v4

        def lam5(t):
            return og[2] + (t - t0) * v5

        def lam6(t):
            return og[3] + (t - t0) * v6

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append((lam1(tj), (lam4(tj), lam5(tj), lam6(tj))))
        return stack
    def update_change(self, val, radius=1, origin=ORIGIN):
        self.change(*val)

class Block(Blobject):
    def __init__(self, xDepth=1, yDepth=1, zDepth=1, origin=ORIGIN, leColor=BLACK):
        """Generates a block.

        Args:
            xDepth (float, optional): x-depth of Block. Defaults to 1.
            yDepth (float, optional): y-depth of Block. Defaults to 1.
            zDepth (float, optional): z-depth of Block. Defaults to 1.
            origin ([type], optional): origin of Block. Defaults to ORIGIN.
            leColor ([type], optional): color of Block. Defaults to BLACK.

        Raises:
            CustomError: Block xDepth must be greater than 0
            CustomError: Block yDepth must be greater than 0
            CustomError: Block zDepth must be greater than 0
        """
        super().__init__()
        # poor value checking
        if xDepth <= 0:
            raise CustomError("Block xDepth must be greater than 0")
        if yDepth <= 0:
            raise CustomError("Block yDepth must be greater than 0")
        if zDepth <= 0:
            raise CustomError("Block zDepth must be greater than 0")
        self.xDepth = xDepth
        self.yDepth = yDepth
        self.zDepth = zDepth
        self.origin = origin
        # construct unique ID
        self.id = self.createID("block")
        bpy.ops.mesh.primitive_cube_add(size=1, location=self.origin)
        bpy.ops.transform.resize(
            value=(self.xDepth, 1, 1),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(True, False, False),
            mirror=True,
        )
        bpy.ops.transform.resize(
            value=(1, self.yDepth, 1),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(False, True, False),
            mirror=True,
        )
        bpy.ops.transform.resize(
            value=(1, 1, self.zDepth),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(False, False, True),
            mirror=True,
        )
        # determine name suffix for block
        strI = self.stringID(self.id)
        self.name = ["block" + strI]
        C.view_layer.objects.active.name = self.name[0]
        self.color(leColor)

    def copy(self):
        """
        Returns a reference to a deep-copied Block()
        """
        return Block(
            self.xDepth, self.yDepth, self.zDepth, self.origin, self.getColor()
        )

    def change(self, xDepth=1, yDepth=1, zDepth=1, origin=ORIGIN):
        """
        Changes the Block() to have different depths and a different origin.
        NOTE: assumes that the block is oriented regularly or unrotated into some
        fancy orientation.
        """
        self.delete()
        self.__init__(xDepth, yDepth, zDepth, origin, self.getColor())
    def init_change(
        self, t0=0, tf=1, rate=EASE_IN_OUT, xDepth=1, yDepth=1, zDepth=1, origin=ORIGIN
    ):
        # error checking
        if xDepth <= 0 or yDepth <= 0 or zDepth <= 0:
            raise CustomError("xDepth, yDepth, and zDepth must all be positive values")
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # create a default linear scaling in distance object
        (x0, y0, z0) = self.origin
        (x1, y1, z1) = origin
        v1 = (xDepth - self.xDepth) / (tf - t0)
        v2 = (yDepth - self.yDepth) / (tf - t0)
        v3 = (zDepth - self.zDepth) / (tf - t0)
        v4 = (x1 - x0) / (tf - t0)
        v5 = (y1 - y0) / (tf - t0)
        v6 = (z1 - z0) / (tf - t0)
        og = [self.xDepth, self.yDepth, self.zDepth, x0, y0, z0]
        # define linear shifts
        def lam1(t):
            return og[0] + (t - t0) * v1

        def lam2(t):
            return og[1] + (t - t0) * v2

        def lam3(t):
            return og[2] + (t - t0) * v3

        def lam4(t):
            return og[3] + (t - t0) * v4

        def lam5(t):
            return og[4] + (t - t0) * v5

        def lam6(t):
            return og[5] + (t - t0) * v6

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append((lam1(tj), lam2(tj), lam3(tj), (lam4(tj), lam5(tj), lam6(tj))))
        return stack
    def update_change(self, val, xDepth=1, yDepth=1, zDepth=1, origin=ORIGIN):
        self.change(*val)

class BoundingBox(NodeWires):
    def __init__(self, right=1, top=1, left=-1, bottom=-1, thickness=0.1):
        """Creates a bounding box out of NodeWires.

        Args:
            right (float, optional): Right boundary of box. Defaults to 1.
            top (float, optional): Top boundary of box. Defaults to 1.
            left (float, optional): Left boundary of box. Defaults to -1.
            bottom (float, optional): Bottom boundary of box. Defaults to -1.
            thickness (float, optional): Thickness of box. Defaults to 0.1.
        """
        # create nodes
        nodes = [
            (right, top, 0),
            (left, top, 0),
            (left, bottom, 0),
            (right, bottom, 0),
            (right, top, 0),
        ]
        super().__init__(nodes, thickness)

class Curve(Blobject):
    def __init__(self, coords=[], color=BLACK, thickness=0.05):
        """
        Generates a curve from a set of coordinates or nodes. Each coordinate is
        expected to be a 3-tuple.

        Args:
            coords (list, optional): A list of coordinates in space that draw out
                the curve. Defaults to [].
            color (tuple, optional): Color of Curve. Defaults to BLACK.
            thickness (float, optional): Thickness of Curve. NOTE: curve also
                creates a bezier circle object in the UI, but it's invisible in
                output renders. Defaults to 0.05.

        Raises:
            CustomError: coords must be a list with at least two points
        """
        super().__init__()
        # error checking for coords
        if len(coords) <= 1:
            raise CustomError("coords must be a list with at least two points")
        # create proper normal
        endingPoint = coords[-1]
        previousPoint = coords[-2]
        self.normal = difference(previousPoint, endingPoint)
        # first, generate a new name/id for this object
        self.id = self.createID("peeps_curve")
        # determine name suffix
        strI = self.stringID(self.id)
        self.name = ["peeps_curve" + strI]
        # create the curve datablock
        curveData = D.curves.new(self.name[0], type="CURVE")
        curveData.dimensions = "3D"
        curveData.resolution_u = 1
        # map coords to spline
        polyline = curveData.splines.new("NURBS")
        polyline.points.add(len(coords) - 1)
        for i, coord in enumerate(coords):
            x, y, z = coord
            polyline.points[i].co = (x, y, z, 1)
        # create object
        curveOB = D.objects.new(self.name[0], curveData)
        # attach to scene and validate context
        C.collection.objects.link(curveOB)
        C.view_layer.objects.active = curveOB
        curveOB.select_set(True)
        obj = C.active_object.data
        # Which parts of the curve to extrude ['HALF', 'FRONT', 'BACK', 'FULL']
        obj.fill_mode = "FULL"
        # Breadth of extrusion
        obj.extrude = 0.05
        # Depth of extrusion
        obj.bevel_depth = 0.1
        # Smoothness of the segments on the curve
        obj.resolution_u = 1
        obj.render_resolution_u = 1
        # create bevel control curve if it doesn't already exist
        try:
            bevel_control = D.objects["bevel_control_" + str(thickness)]
        except KeyError:
            bpy.ops.curve.primitive_bezier_circle_add(
                radius=thickness, enter_editmode=True
            )
            bevel_control = C.active_object
            bevel_control.data.name = bevel_control.name = "bevel_control_" + str(
                thickness
            )
        # set the main curve's bevel control to the bevel control curve
        obj.bevel_object = bevel_control
        bpy.ops.object.mode_set(mode="OBJECT")
        # color field line
        self.color(color)

class CurvyArrow(Blobject):
    def __init__(self, length=1, centerDist=1, origin=ORIGIN, normalInput=(0, 0, 1)):
        """Creates a Vector(), then curves it.

        Args:
            length (float, optional): length of initial Vector(). Defaults to 1.
            centerDist (float, optional): radius of curvature of the arrow.
                Defaults to 1.
            origin (tuple, optional): origin of CurvyArrow. Defaults to ORIGIN.
            normalInput (tuple, optional): The 3-tuple normal axis about which the
                CurvyArrow twists. Defaults to (0, 0, 1).
        """
        super().__init__()
        # error-checking on poor inputs
        if centerDist < 1:
            centerDist = 1
        if length > TAU * centerDist:
            length = TAU * centerDist
        self.length = length
        self.centerDist = centerDist
        self.origin = origin
        # start by creating a Vector() situated at the global origin
        v = Vector(self.length, 0, 0)
        selectOnly(v.name)
        C.view_layer.objects.active = D.objects[v.name[0]]
        currObj = C.active_object
        # create distinct id by checking if other arrows exist - goes up to 100 arrows
        self.id = self.createID("curvy_arrow")
        # determine name suffix (which number arrow is this?)
        strI = self.stringID(self.id)
        # change name
        self.name = ["curvy_arrow" + strI]
        currObj.name = self.name[0]
        # curve arrow by adding loopcuts and a simple-deform bend
        # override context for loopcut
        win = C.window
        scr = win.screen
        areas3d = [area for area in scr.areas if area.type == "VIEW_3D"]
        region = [region for region in areas3d[0].regions if region.type == "WINDOW"]
        override = {
            "window": win,
            "screen": scr,
            "area": areas3d[0],
            "region": region[0],
            "scene": C.scene,
        }
        # perform loopcut
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.loopcut_slide(
            override,
            MESH_OT_loopcut={
                "number_cuts": 60,
                "smoothness": 0,
                "falloff": "INVERSE_SQUARE",
                "object_index": 0,
                "edge_index": 6,
                "mesh_select_mode_init": (True, False, False),
            },
            TRANSFORM_OT_edge_slide={
                "value": 0,
                "single_side": False,
                "use_even": False,
                "flipped": False,
                "use_clamp": True,
                "mirror": True,
                "snap": False,
                "snap_target": "CLOSEST",
                "snap_point": ORIGIN,
                "snap_align": False,
                "snap_normal": ORIGIN,
                "correct_uv": True,
                "release_confirm": True,
                "use_accurate": False,
            },
        )
        bpy.ops.object.mode_set(mode="OBJECT")
        # perform bend
        bpy.ops.object.modifier_add(type="SIMPLE_DEFORM")
        C.object.modifiers["SimpleDeform"].deform_method = "BEND"
        C.object.modifiers["SimpleDeform"].angle = length / centerDist
        # shift arrow to its origin
        self.shift(origin[0], origin[1] - centerDist, origin[2])
        self.distVec = mut.Vector((0, -centerDist, 0))
        # normal transform
        self.transform(normal=normalInput)
        self.color(BLACK)

    def transform(self, normal=ORIGIN, twist=0, twistDeg=False):
        """Twists the CurvyArrow.

        Args:
            normal (tuple, optional): 3-tuple axis about which CurvyArrow twists.
                Defaults to ORIGIN.
            twist (float, optional): Twist angle. Defaults to 0.
            twistDeg (bool, optional): Determines whether or not twist is in degrees
                or radians. Defaults to False, so radians.
        """
        # default behavior (usually for no orientation switch, only twist)
        if normal == ORIGIN:
            normal = self.normal
        # correct twistDeg
        if twistDeg:
            twist *= PI / 180
        # retrieve the vector
        strI = self.stringID(self.id)
        # select only the relevant vector
        selectOnly(["curvy_arrow" + strI])
        obj = D.objects["curvy_arrow" + strI]
        # define new vector
        ogAxis = mut.Vector(self.normal)
        newAxis = mut.Vector(normal)
        # determine quaternions
        q1 = computeQuaternion(ogAxis, newAxis)
        q2 = mut.Quaternion(normal, twist)
        # perform transformations
        # first, transform to the point of rotation of the object
        tupleTransform = tuple(-self.distVec)
        tupleInverse = tuple(self.distVec)
        bpy.ops.transform.translate(
            value=tupleTransform,
            orient_type="LOCAL",
            constraint_axis=(False, False, True),
            mirror=True,
        )
        # quaternion rotation
        obj.rotation_mode = "QUATERNION"
        obj.rotation_quaternion = q2 @ q1 @ obj.rotation_quaternion
        # undo initial transformation
        bpy.ops.transform.translate(
            value=tupleInverse,
            orient_type="LOCAL",
            constraint_axis=(False, False, True),
            mirror=True,
        )
        # reset normal
        self.normal = normal
    def init_transform(
        self, t0=0, tf=1, rate=EASE_IN_OUT, normal=ORIGIN, twist=0, twistDeg=False
    ):
        # error checking
        if normal == ORIGIN:
            raise CustomError(
                "Calling init_transform() requires a non-zero rotation axis to be passed in as normal"
            )
        t = interpolate(t0, tf, rate)
        t.pop(0)
        diffs = np.diff(interpolate(0, twist, rate, numIntervals=len(t))).tolist()
        stack = deque()
        diffs.reverse()
        for smallAngle in diffs:
            stack.append(smallAngle)
        return stack
    def update_transform(self, val, normal=ORIGIN, twist=0, twistDeg=False):
        # error checking
        if normal == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.transform(normal, val, twistDeg)

class Cylinder(Blobject):
    def __init__(self, radius=1, height=1, origin=ORIGIN):
        """Generates a cylinder with some radius and height centered at some origin.

        Args:
            radius (float, optional): radius of Cylinder. Defaults to 1.
            height (float, optional): height of Cylinder. Defaults to 1.
            origin (tuple, optional): origin of Cylinder. Defaults to ORIGIN.

        Raises:
            CustomError: radius must be greater than 0
            CustomError: height must be greater than 0
        """
        super().__init__()
        # poor value checking
        if radius <= 0:
            raise CustomError("Cylinder radius must be greater than 0")
        if height <= 0:
            raise CustomError("Cylinder height must be greater than 0")
        self.radius = radius
        self.height = height
        self.origin = origin
        # construct unique ID
        self.id = self.createID("cylinder")
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=100, radius=self.radius, depth=self.height, location=self.origin
        )
        bpy.ops.object.shade_smooth()
        # determine name suffix for cyllinder
        strI = self.stringID(self.id)
        self.name = ["cylinder" + strI]
        C.view_layer.objects.active.name = self.name[0]

class Ellipse(Curve):
    def __init__(
        self,
        xAxis=1,
        yAxis=1,
        origin=ORIGIN,
        color=BLACK,
        thickness=0.05,
        resolution=100,
    ):
        """Creates an ellipse.

        Args:
            xAxis (float, optional): x-axis of ellipse. Defaults to 1.
            yAxis (float, optional): y-axis of ellipse. Defaults to 1.
            origin (tuple, optional): centered origin of ellipse. Defaults to
                ORIGIN.
            color (tuple, optional): 4-tuple (R, G, B, 1) that defines color of
                ellipse. Defaults to BLACK.
            thickness (float, optional): thickness of ellipse. Defaults to 0.05.
            resolution (float, optional): resolution of ellipse, i.e. the number of
                points used to define the Curve() created by the ellipse. Defaults
                to 100.
        """
        # generate the coordinates
        angs = interpolate(0, 2 * PI, LINEAR, resolution)
        coords = []
        for ang in angs:
            coords.append(
                (origin[0] + xAxis * np.cos(ang), origin[1] + yAxis * np.sin(ang), 0)
            )
        super().__init__(coords, color, thickness)

class FieldLine(Blobject):
    def __init__(self, coords=[], color=BLACK):
        """
        Generates a field-line (like electric or magnetic) from a list of coordinates.

        Args:
            coords (list, optional): list of nodes, each of which is a 3-tuple that
                defines some point in space. The list defines how the field-line
                evolves in space. Defaults to [].
            color (tuple, optional): 4-tuple that defines the color of the field-line.
                Defaults to BLACK.

        Raises:
            CustomError: coords must be a list with at least two points
        """
        super().__init__()
        # error checking for coords
        if len(coords) <= 1:
            raise CustomError("coords must be a list with at least two points")
        # create proper normal
        endingPoint = coords[-1]
        previousPoint = coords[-2]
        self.normal = difference(previousPoint, endingPoint)
        # first, generate a new name/id for this object
        self.id = self.createID("field_line")
        # determine name suffix
        strI = self.stringID(self.id)
        self.name = ["field_line" + strI, "field_head" + strI]
        # create the curve datablock
        curveData = D.curves.new(self.name[0], type="CURVE")
        curveData.dimensions = "3D"
        # WAS ORIGINALLY 2
        curveData.resolution_u = 1
        # map coords to spline
        polyline = curveData.splines.new("NURBS")
        polyline.points.add(len(coords))
        for i, coord in enumerate(coords):
            x, y, z = coord
            polyline.points[i].co = (x, y, z, 1)
        # create object
        curveOB = D.objects.new(self.name[0], curveData)
        # attach to scene and validate context
        C.collection.objects.link(curveOB)
        C.view_layer.objects.active = curveOB
        curveOB.select_set(True)
        obj = C.active_object.data
        # Which parts of the curve to extrude ['HALF', 'FRONT', 'BACK', 'FULL']
        obj.fill_mode = "FULL"
        # Breadth of extrusion
        obj.extrude = 0.05
        # Depth of extrusion
        obj.bevel_depth = 0.1
        # Smoothness of the segments on the curve
        # ORIGINALLY 20 AND 32
        obj.resolution_u = 1
        obj.render_resolution_u = 1
        # create bevel control curve if it doesn't already exist
        try:
            bevel_control = D.objects["bevel_control"]
        except KeyError:
            bpy.ops.curve.primitive_bezier_circle_add(radius=0.05, enter_editmode=True)
            bevel_control = C.active_object
            bevel_control.data.name = bevel_control.name = "bevel_control"
        # set the main curve's bevel control to the bevel control curve
        obj.bevel_object = bevel_control
        bpy.ops.object.mode_set(mode="OBJECT")
        # now, create the cone-head
        # create vector head
        bpy.ops.mesh.primitive_cone_add(radius1=0.5, radius2=0, depth=0.5)
        cone = C.active_object
        bpy.ops.object.shade_smooth()
        # place the bottom of the cone in the right spot
        bpy.ops.transform.translate(
            value=(0, 0, 0.25),
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        bpy.ops.transform.translate(
            value=coords[-1],
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
        cone.name = self.name[1]
        # orient cone properly
        # define new vector
        zAxis = mut.Vector((0, 0, 1))
        # quaternion rotation
        try:
            cone.rotation_mode = "QUATERNION"
            cone.rotation_quaternion = computeQuaternion(zAxis, mut.Vector(self.normal))
        except:
            # indeterminate quaternion means it points in the negative z-axis
            bpy.ops.transform.rotate(
                value=PI,
                orient_axis="Y",
                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                constraint_axis=(False, True, False),
                mirror=True,
            )
        # now that the head is in the right spot, apply a constraint to it
        bpy.ops.object.constraint_add(type="CHILD_OF")
        C.object.constraints["Child Of"].target = D.objects[self.name[0]]
        # color field line
        self.color(color)

class Helix(NodeWires):
    def __init__(
        self,
        radius=5,
        pitch=2,
        length=10,
        origin=ORIGIN,
        thickness=0.1,
        color=BLACK,
        ends=True,
        endLength=3,
    ):
        """Creates a Helix object.

        Args:
            radius (float, optional): radius of helical spiral. Defaults to 5.
            pitch (float, optional): distance between individual circular spirals.
                Defaults to 2.
            length (float, optional): distance between each end of the Helix. Defaults
                to 10.
            origin (tuple, optional): origin of Helix. Defaults to ORIGIN.
            thickness (float, optional): thickness of Helix. Defaults to 0.1.
            color (tuple, optional): color of Helix. Defaults to BLACK.
            ends (bool, optional): determines whether or not ends jut out of the
                Helix, as you might see on a spring diagram. Defaults to True.
            endLength (float, optional): length of Helix ends. Defaults to 3.
        """
        # create nodes
        nodes = []
        x = lambda t: radius * np.cos(t)
        y = lambda t: radius * np.sin(t)
        z = lambda t: pitch / TAU * t - length / 2
        # points split into 0.01 segments
        t = 0
        while z(t) < length / 2:
            nodes.append((x(t), y(t), z(t)))
            t += 0.1
        if ends:
            nodes.insert(0, (0, 0, z(0)))
            nodes.insert(0, (0, 0, z(0) - endLength))
            nodes.append((0, 0, z(t)))
            nodes.append((0, 0, z(t) + endLength))
        self.nodes = nodes
        self.radius = radius
        self.pitch = pitch
        self.length = length
        self.thickness = thickness
        self.realLength = length / pitch * np.sqrt(pitch ** 2 + (TAU * radius) ** 2)
        super().__init__(nodes, thickness, color, 0.1, 10)
        self.shift(*origin)

class HollowCylinder(Blobject):
    def __init__(self, radius=1, height=1, origin=ORIGIN, thickness=0.1):
        """Just what you'd expect: a Cylinder, but hollow.

        Args:
            radius (float, optional): outer radius of HollowCylinder. Defaults to 1.
            height (float, optional): height of HollowCylinder. Defaults to 1.
            origin (tuple, optional): origin of HollowCylinder. Defaults to ORIGIN.
            thickness (float, optional): thickness of HollowCylinder. Defaults to 0.1.

        Raises:
            CustomError: radius must be greater than 0
            CustomError: height must be greater than 0
            CustomError: thickness must be greater than 0
        """
        super().__init__()
        # poor value checking
        if radius <= 0:
            raise CustomError("Cylinder radius must be greater than 0")
        if height <= 0:
            raise CustomError("Cylinder height must be greater than 0")
        if thickness <= 0:
            raise CustomError("Cylinder thickness must be greater than 0")
        self.radius = radius
        self.height = height
        self.origin = origin
        self.thickness = thickness
        cuttingCylinder = Cylinder(radius - thickness, height + 0.1, origin)
        mainCylinder = Cylinder(radius, height, origin)
        # use cuttingCylinder to cut mainCylinder
        bpy.ops.object.modifier_add(type="BOOLEAN")
        C.object.modifiers["Boolean"].object = D.objects[cuttingCylinder.name[0]]
        bpy.ops.object.modifier_apply(apply_as="DATA", modifier="Boolean")
        delete(cuttingCylinder)
        self.name = mainCylinder.name

class Line(Blobject):
    def __init__(self, p1=ORIGIN, p2=ORIGIN, width=0.02, numSegments=1):
        """A simple line between two points (basically a reoriented Cylinder).

        Args:
            p1 (tuple, optional): 3-tuple that defines first end of Line. Defaults
                to ORIGIN.
            p2 (tuple, optional): 3-tuple that defines second end of Line. Defaults
                to ORIGIN.
            width (float, optional): width of Line. Defaults to 0.02.
            numSegments (int, optional): number of segments of Line. Example: 3
                segments would result in a dashed line that has 3 individual parts.
                Defaults to 1, in which case the Line is not dashed.

        Raises:
            CustomError: Line() must have non-zero length.
            CustomError: numSegments must be an integer greater than 0.
        """
        super().__init__()
        self.p1 = p1
        self.p2 = p2
        self.width = width
        self.numSegments = numSegments
        # error checking
        p3 = mut.Vector((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
        if p3.length == 0:
            raise CustomError("Line() has zero-length - crashing...")
        if numSegments == 1:
            Cylinder(radius=width, height=p3.length)
            currObj = C.active_object
            self.id = self.createID("line")
            strI = self.stringID(self.id)
            self.name = ["line" + strI]
            currObj.name = self.name[0]
            self.shift(*[i + j / 2 for i, j in zip(p1, p3)])
            self.transform(tuple(p3))
            self.color(BLACK)
        else:
            # error checking for numSegments
            if numSegments < 1:
                raise CustomError("numSegments must be greater than 0")
            numSegments = round(numSegments)
            self.id = self.createID("line")
            strI = self.stringID(self.id)
            # now, compute the positions of the segments
            numPortions = 2 * numSegments - 1
            portionLength = p3.length / numPortions
            segments = []
            self.name = []
            for portion in range(numPortions):
                # only create portions at even increments
                if portion % 2 == 0:
                    segments.append(
                        Cylinder(
                            width,
                            portionLength,
                            (0, 0, portionLength / 2 + portion * portionLength),
                        )
                    )
                    currObj = C.active_object
                    self.name.append("line" + strI + ".seg." + str(portion))
                    currObj.name = self.name[-1]
                    # place origin at world-origin
                    bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
            self.shift(*p1)
            self.transform(tuple(p3))
            self.color(BLACK)

class PointCharge(Blobject):
    def __init__(
        self,
        radius=1,
        origin=ORIGIN,
        strLabel="+",
        charge=ELEM_CHARGE,
        mass=MASS_PROTON,
        texScale=None,
    ):
        """A nifty representation of a PointCharge: just a Ball with a Tex indicator.

        Args:
            radius (float, optional): radius of Ball. Defaults to 1.
            origin (tuple, optional): origin of Ball. Defaults to ORIGIN.
            strLabel (str, optional): the Tex label for the Ball or PointCharge.
                Defaults to "+".
            charge (float, optional): a floating-point representation of the charge on
                the PointCharge. This is useful for simulating electrodynamics (see
                standalone functions below). Defaults to ELEM_CHARGE.
            mass (float, optional): a floating-point representation of the mass of
                the PointCharge. This is useful for simulating electrodynamics (see
                standalone functions below). Defaults to MASS_PROTON.
            texScale (float, optional): the scale of the Tex associated with the
                PointCharge. If unspecified, a scale is automatically chosen based on
                the size of the Ball. Defaults to None.
        """
        self.tampered = []
        self.texNames = []
        self.radius = radius
        self.differential = 0.1
        self.origin = ORIGIN
        self.charge = charge
        self.mass = mass
        self.normal = (0, 0, 1)
        self.labelString = strLabel
        # create the ball
        self.ball = Ball(radius)
        self.id = self.ball.id
        # now, create the tex to go with it
        if strLabel:
            if texScale:
                self.label = Tex("\\text{" + strLabel + "}", texScale)
            elif len(strLabel) == 1:
                self.label = Tex("\\text{" + strLabel + "}", radius / 2)
            else:
                self.label = Tex("\\text{" + strLabel + "}", radius / 4)
            # shift the tex up
            self.label.shift(0, 0, radius + self.differential)
            self.label.color(BLACK)
            self.name = [self.ball.name, self.label.name]
        else:
            self.label = False
            self.name = [self.ball.name]
        self.relativePosition = (0, 0, radius + self.differential)
        # reduce
        self.name = [item for sublist in self.name for item in sublist]
        self.shift(origin[0], origin[1], origin[2])

    def color(self, theColor=WHITE, ignoreTampered=False):
        """
        Colors the Ball: you only want to color the Ball part and not the Tex part,
        so that the black Tex contrasts with the Ball and is visible.

        Args:
            theColor (tuple, optional): 4-tuple that defines the color of the Ball.
                Defaults to WHITE.
            ignoreTampered (bool, optional): necessary for Tex coloring. Probably best
                to just leave this like it is. Defaults to False.
        """
        self.ball.color(theColor)

    def shift(self, x=0, y=0, z=0, xLam=None, yLam=None, zLam=None):
        """
        A separate shift function is necessary to define the shift of a PointCharge,
        because one has to take into account how to shift the Tex. The Tex is shifted
        such that it continues to face the camera no matter how the Ball is shifted.

        Args:
            x (float, optional): x-shift. Defaults to 0.
            y (float, optional): y-shift. Defaults to 0.
            z (float, optional): z-shift. Defaults to 0.
            xLam (lambda, optional): used to x-shift via a certain lambda function.
                Rarely needed, but the option exists. Defaults to None.
            yLam (lambda, optional): used to y-shift via a certain lambda function.
                Rarely needed, but the option exists. Defaults to None.
            zLam (lambda, optional): used to z-shift via a certain lambda function.
                Rarely needed, but the option exists. Defaults to None.
        """
        super().shift(x, y, z, xLam, yLam, zLam)
        if self.label:
            self.label.origin = tuple(map(operator.add, self.label.origin, (x, y, z)))
            self.label.cameraTrack()
            # change placement of label, based off of its relative position
            self.label.shift(
                -self.relativePosition[0],
                -self.relativePosition[1],
                -self.relativePosition[2],
            )
            loc = C.scene.camera.location
            o = self.origin
            connection = (loc[0] - o[0], loc[1] - o[1], loc[2] - o[2])
            mag = np.sqrt(connection[0] ** 2 + connection[1] ** 2 + connection[2] ** 2)
            newDist = self.radius + self.differential
            self.label.shift(
                connection[0] * newDist / mag,
                connection[1] * newDist / mag,
                connection[2] * newDist / mag,
            )
            self.relativePosition = (
                connection[0] * newDist / mag,
                connection[1] * newDist / mag,
                connection[2] * newDist / mag,
            )
            self.label.cameraTrack()

    def shiftByPath(self, nodes=[]):
        """
        Used to shift a charge via a path of nodes in a render. NOTE: only supports a
        rate of LINEAR, by certain necessities.

        Args:
            nodes (list, optional): A list of coordinates (3-tuple) that define points
                to shift to. Defaults to [].
        """
        # just move to the last node if not rendering
        self.shift(*subtraction(nodes[-1], self.origin))
    def init_shiftByPath(self, t0=0, tf=4, rate=LINEAR, nodes=[]):
        # first, determine the total distance of the path
        totalDistance = 0
        curr = self.origin
        for node in nodes:
            dist = subtraction(node, curr)
            totalDistance += mag(dist)
            curr = node
        # find the total number of frames
        totalFrames = (tf - t0) * FRAME_RATE
        distancePerFrame = totalDistance / totalFrames
        # now move distancePerFrame in the direction of each node, watching if you overshoot
        t = interpolate(t0, tf, LINEAR)
        t.pop(0)
        stack = deque()
        curr = self.origin
        prev = curr
        for i, node in zip(range(len(nodes)), nodes):
            # check if already at node
            if curr == node:
                continue
            # determine the direction
            correctDirection = mut.Vector(subtraction(node, curr)).normalized()
            currentDirection = mut.Vector(subtraction(node, curr)).normalized()
            while currentDirection.dot(correctDirection) > 0:
                distToMove = list(currentDirection * distancePerFrame)
                stack.append(distToMove)
                prev = curr
                curr = tuple(addition(curr, distToMove))
                currentDirection = mut.Vector(subtraction(node, curr)).normalized()
            # we've moved too far - revert
            stack.pop()
            curr = prev
            # what distance do we have left to traverse?
            distanceLeft = mag(subtraction(node, curr))
            # go to node and take that distance away from the first step for the next node
            curr = node
            try:
                nextNode = nodes[i + 1]
            except IndexError:
                break
            currentDirection = mut.Vector(subtraction(nextNode, curr)).normalized()
            distToMove = list(currentDirection * (distancePerFrame - distanceLeft))
            curr = tuple(addition(curr, distToMove))
            stack.append(list(subtraction(curr, prev)))
        stack.reverse()
        return stack
    def update_shiftByPath(self, val, nodes=[]):
        self.shift(*val)

class Ramp(Blobject):
    def __init__(self, length=1, height=1, depth=1, origin=ORIGIN):
        """Creates a ramp by altering the mesh of a Block.

        Args:
            length (float, optional): length of Ramp. Defaults to 1.
            height (float, optional): height of Ramp. Defaults to 1.
            depth (float, optional): depth of Ramp. Defaults to 1.
            origin (tuple, optional): origin of Ramp. Defaults to ORIGIN.

        Raises:
            CustomError: length must be greater than 0
            CustomError: height must be greater than 0
            CustomError: depth must be greater than 0
        """
        super().__init__()
        # poor value checking
        if length <= 0:
            raise CustomError("Ramp length must be greater than 0")
        if height <= 0:
            raise CustomError("Ramp height must be greater than 0")
        if depth <= 0:
            raise CustomError("Ramp depth must be greater than 0")
        self.length = length
        self.height = height
        self.depth = depth
        self.origin = origin
        # construct unique ID
        self.id = self.createID("ramp")
        bpy.ops.mesh.primitive_cube_add(size=2, location=self.origin)
        # determine name suffix for ramp
        strI = self.stringID(self.id)
        self.name = ["ramp" + strI]
        C.view_layer.objects.active.name = self.name[0]
        # alter mesh to create ramp by merging vertices
        # get the active mesh
        rampMesh = C.object.data
        # get bmesh representation, by first creating empty bmesh
        bm = bmesh.new()
        # fill in bmesh
        bm.from_mesh(rampMesh)
        # modify vertices
        for v in bm.verts:
            if v.co.x == 1 and v.co.z == 1:
                v.co.z = -1
        # write bmesh back to active mesh
        bm.to_mesh(rampMesh)
        # delete bmesh
        bm.free()
        bpy.ops.transform.resize(
            value=(self.length / 2, 1, 1),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(True, False, False),
            mirror=True,
        )
        bpy.ops.transform.resize(
            value=(1, self.depth / 2, 1),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(False, True, False),
            mirror=True,
        )
        bpy.ops.transform.resize(
            value=(1, 1, self.height / 2),
            orient_type="LOCAL",
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            orient_matrix_type="LOCAL",
            constraint_axis=(False, False, True),
            mirror=True,
        )

class RelativeNodeWires(NodeWires):
    def __init__(
        self, nodes=[], thickness=0.1, color=BLACK, curvatureRadius=0.1, resolution=100
    ):
        """
        Creates a NodeWires with a list of relatively-defined nodes, not
        absolutely-defined nodes (very nifty). For example, the instantiations
        NodeWires([
            (0, 0, 0),
            (0, 5, 0),
            (5, 5, 0),
            (5, 0, 0)
        ])
        and
        RelativeNodeWires([
            (0, 0, 0),
            (0, 5, 0),
            (5, 0, 0),
            (0, -5, 0)
        ])
        create exactly the same object.

        Args:
            nodes (list, optional): list of nodes defined relative to one another.
                The first node is an absolute node and each subsequent node is defined
                relative to the previous node. Defaults to [].
            thickness (float, optional): thickness of NodeWires. Defaults to 0.1.
            color (tuple, optional): 4-tuple that defines color of NodeWires.
                Defaults to BLACK.
            curvatureRadius (float, optional): radius of curvature between NodeWire
                points. Defaults to 0.1.
            resolution (int, optional): number of extra points defined to join between
                NodeWire bends. Defaults to 100.
        """
        super().__init__(
            computeAbsoluteNodes(nodes), thickness, color, curvatureRadius, resolution
        )

class Ring(Blobject):
    def __init__(self, radius=1, thickness=1, origin=ORIGIN):
        """Creates a simple ring or torus.

        Args:
            radius (float, optional): radius of ring outline. Defaults to 1.
            thickness (float, optional): thickness of Ring. Defaults to 1.
            origin (tuple, optional): centered origin of Ring. Defaults to ORIGIN.

        Raises:
            CustomError: thickness must be greater than 0
            CustomError: radius must be greater than thickness
        """
        super().__init__()
        # poor value checking
        if thickness <= 0:
            raise CustomError("Ring thickness must be greater than 0")
        if radius < thickness:
            raise CustomError("Ring radius must be greater than Ring thickness")
        self.radius = radius
        self.thickness = thickness
        self.origin = origin
        # construct unique ID
        self.id = self.createID("ring")
        bpy.ops.mesh.primitive_torus_add(
            align="WORLD",
            location=self.origin,
            rotation=(0, 0, 0),
            major_segments=100,
            minor_segments=100,
            major_radius=self.radius,
            minor_radius=self.thickness,
            abso_major_rad=1.25,
            abso_minor_rad=0.75,
        )
        bpy.ops.object.shade_smooth()
        # determine name suffix for ramp
        strI = self.stringID(self.id)
        self.name = ["ring" + strI]
        C.view_layer.objects.active.name = self.name[0]

    def change(self, radius=1, origin=ORIGIN):
        """
        Changes the ring into a ring of different radius and origin. NOTE: assumes
        the ring hasn't been oriented into some weird orientation.

        Args:
            radius (float, optional): new radius of Ring. Defaults to 1.
            origin (tuple, optional): new origin of Ring. Defaults to ORIGIN.
        """
        leColor = self.getColor()
        isTransparent = self.isTransparent
        self.delete()
        self.__init__(radius, self.thickness, origin)
        self.color(leColor)
        if isTransparent:
            self.transparent(self.currentAlpha)
    def init_change(self, t0=0, tf=1, rate=EASE_IN_OUT, radius=1, origin=ORIGIN):
        # error checking
        if radius <= 0:
            raise CustomError("radius must be a non-zero positive value")
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # create a default linear scaling
        (x0, y0, z0) = self.origin
        (x1, y1, z1) = origin
        v1 = (radius - self.radius) / (tf - t0)
        v4 = (x1 - x0) / (tf - t0)
        v5 = (y1 - y0) / (tf - t0)
        v6 = (z1 - z0) / (tf - t0)
        og = [self.radius, x0, y0, z0]
        # define linear shifts
        def lam1(t):
            return og[0] + (t - t0) * v1

        def lam4(t):
            return og[1] + (t - t0) * v4

        def lam5(t):
            return og[2] + (t - t0) * v5

        def lam6(t):
            return og[3] + (t - t0) * v6

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append((lam1(tj), (lam4(tj), lam5(tj), lam6(tj))))
        return stack
    def update_change(self, val, radius=1, origin=ORIGIN):
        self.change(*val)

class SVG(Blobject):
    def __init__(self, expression, scale=1, origin=ORIGIN):
        """
        Creates a visible SVG in the UI out of an SVG that exists on your hard-drive.
        NOTE: these SVG's are expected to be named as "_<expression>.svg" where
        <expression> is passed into the constructor as expression.

        Args:
            expression (str): expression derived from svg filename.
            scale (int, optional): scale of SVG object. This is a scale-factor
                that appends to the scaling done by SVG_SCALING (see the top of this
                file). Defaults to 1.
            origin (tuple, optional): origin of SVG. Defaults to ORIGIN.

        Raises:
            CustomError: there must exist a scaling in SVG_SCALING
        """
        super().__init__()
        self.expression = expression
        # deselect everything
        selectOnly([])
        # get objects before import
        names_pre_import = set([o.name for o in C.scene.objects])
        # import svg
        scalerValue = False
        try:
            scalerValue = SVG_SCALING[expression]
        except:
            if not scalerValue:
                raise CustomError("scaling doesn't exist in SVG_SCALING")
        bpy.ops.import_curve.svg(
            filepath=os.path.join(SVG_DIR, "_" + expression + ".svg")
        )
        # get objects after import
        names_post_import = set([o.name for o in C.scene.objects])
        # differential objects are newly added objects
        new_object_names = names_post_import.difference(names_pre_import)
        self.name = [name for name in new_object_names]
        for name in new_object_names:
            o = C.scene.objects[name]
            o.select_set(True)
            C.view_layer.objects.active = o
        trueScale = scale * scalerValue
        bpy.ops.transform.resize(
            value=(trueScale, trueScale, trueScale),
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        # shift the entire expression into the center
        # first, grab the minimum and maximum location numbers
        minLoc = sys.maxsize
        maxLoc = -sys.maxsize
        self.xLocs = []
        self.yLocs = []
        for leName in new_object_names:
            xLoc = D.objects[leName].location[0]
            self.xLocs.append(D.objects[leName].location[0])
            self.yLocs.append(D.objects[leName].location[1])
            if xLoc > maxLoc:
                maxLoc = xLoc
            if xLoc < minLoc:
                minLoc = xLoc
        # sort the names of the objects based on location
        self.xSortedNames = [
            x for _, x in sorted(zip(self.xLocs, self.name), key=lambda pair: pair[0])
        ]
        self.ySortedNames = [
            x for _, x in sorted(zip(self.yLocs, self.name), key=lambda pair: pair[0])
        ]
        # shift by the average x-location value and move to the mode y-location value
        try:
            self.shift(-(maxLoc + minLoc) / 2, -mode(self.yLocs))
        except:
            self.shift(-(maxLoc + minLoc) / 2, -mean(self.yLocs))
        # now set the origin of each curve in the Tex object to the origin
        for name in new_object_names:
            o = C.scene.objects[name]
            o.select_set(True)
            C.view_layer.objects.active = o
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        self.scale = scale
        self.origin = ORIGIN
        self.shift(*origin)
        self.color(BLACK)

    def rescale(self, scaler=1):
        """Rescales the SVG.

        Args:
            scaler (float, optional): new scale for the SVG. Defaults to 1.
        """
        leColor = self.getColor()
        self.delete()
        self.__init__(self.expression, scaler, self.origin)
        self.color(leColor)
    def init_rescale(self, t0=0, tf=1, rate=EASE_IN_OUT, scaler=1):
        t = interpolate(t0, tf, rate)
        t.pop(0)
        v = (scaler - self.scale) / (tf - t0)
        x = lambda t: self.scale + (t - t0) * v
        stack = deque()
        t.reverse()
        for tj in t:
            stack.append(x(tj))
        return stack
    def update_rescale(self, val, scaler=1):
        self.rescale(val)

class Triangle(Blobject):
    def __init__(self, p1=ORIGIN, p2=(1, 0, 0), p3=(0, 1, 0)):
        """A simple triangle made out of three points.

        Args:
            p1 (tuple, optional): The first point. Defaults to ORIGIN.
            p2 (tuple, optional): The second point. Defaults to (1, 0, 0).
            p3 (tuple, optional): The third point. Defaults to (0, 1, 0).
        """
        super().__init__()
        # error checking
        b1 = Line(p1, p2)
        b2 = Line(p2, p3)
        selectOnly([b1.name[0], b2.name[0]])
        C.view_layer.objects.active = D.objects[b1.name[0]]
        bpy.ops.object.join()
        b3 = Line(p3, p1)
        selectOnly([b1.name[0], b3.name[0]])
        C.view_layer.objects.active = D.objects[b1.name[0]]
        bpy.ops.object.join()
        currObj = C.active_object
        self.id = self.createID("triangle")
        strI = self.stringID(self.id)
        self.name = ["triangle" + strI]
        currObj.name = self.name[0]
        v1 = mut.Vector((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
        v2 = mut.Vector((p3[0] - p1[0], p3[1] - p1[1], p3[2] - p3[2]))
        v3 = v1.cross(v2)
        self.normal = (v3[0], v3[1], v3[2])

class Vector(Blobject):
    def __init__(
        self,
        xProj=1,
        yProj=0,
        zProj=0,
        origin=ORIGIN,
        color=BLACK,
        thickness=None,
        coneRadius=None,
        coneHeight=None,
    ):
        """A useful, modifiable representation of a vector.

        Args:
            xProj (float, optional): the x-component of the Vector. Defaults to 1.
            yProj (float, optional): the y-component of the Vector. Defaults to 0.
            zProj (float, optional): the z-component of the Vector. Defaults to 0.
            origin (tuple, optional): the origin of the Vector. Defaults to ORIGIN.
            color (tuple, optional): the color of the Vector. Defaults to BLACK.
            thickness (float, optional): the thickness of the Vector. If not
                specified, one will be automatically chosen. Defaults to None.
            coneRadius (float, optional): the radius of the cone part of the Vector.
                If not specified, one will be automatically chosen. Defaults to None.
            coneHeight (float, optional): the height of the cone part of the Vector.
                If not specified, one will be automatically chosen. Defaults to None.
        """
        super().__init__()
        self.thickness = thickness
        self.coneRadius = coneRadius
        self.coneHeight = coneHeight
        # create distinct id
        self.id = self.createID("vector")
        # determine name suffix (which number vector is this?)
        strI = self.stringID(self.id)
        # generate name list of components
        self.name = ["vector_body" + strI, "vector_head" + strI]
        # prepare to create vector along z-axis, since cylinder and cone are upright
        vec = mut.Vector((xProj, yProj, zProj))
        mag = vec.length
        # error-checking for magnitude stuff
        if coneRadius == None:
            coneRadius = mag / 2 if mag <= 1 else 0.5
        if coneHeight == None:
            coneHeight = mag / 2 if mag <= 1 else 0.5
        if thickness == None:
            thickness = coneHeight / 5
        # create vector body
        bpy.ops.mesh.primitive_cylinder_add(radius=thickness, depth=mag - coneHeight)
        obj = C.active_object
        bpy.ops.object.shade_smooth()
        obj.name = self.name[0]
        C.scene.cursor.location[2] = -(mag - coneHeight) / 2
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        bpy.ops.transform.translate(
            value=(0, 0, (mag - coneHeight) / 2), constraint_axis=(False, False, True)
        )
        C.scene.cursor.location[2] = mag - coneHeight / 2
        # create vector head
        bpy.ops.mesh.primitive_cone_add(radius1=coneRadius, radius2=0, depth=coneHeight)
        obj = C.active_object
        bpy.ops.object.shade_smooth()
        obj.name = self.name[1]
        C.scene.cursor.location[2] = 0
        # join vector_head and vector_body
        # first, select the vector parts
        selectOnly(self.name)
        C.view_layer.objects.active = D.objects[self.name[0]]
        # now, join them
        bpy.ops.object.join()
        obj = C.active_object
        # change name
        self.name = ["vector" + strI]
        obj.name = self.name[0]
        # shift vector to its origin before constructing proper orientation
        self.shift(origin[0], origin[1], origin[2])
        # define new vector
        zAxis = mut.Vector((0, 0, 1))
        # quaternion rotation
        if np.isclose(vec[0], 0) and np.isclose(vec[1], 0) and vec[2] < 0:
            # indeterminate quaternion means it points in the negative z-axis
            bpy.ops.transform.rotate(
                value=PI,
                orient_axis="Y",
                orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                constraint_axis=(False, True, False),
                mirror=True,
            )
        else:
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = computeQuaternion(zAxis, vec)
        # reset x, y, z magnitudes
        self.normal = (xProj, yProj, zProj)
        self.color(color)

    def copy(self):
        """Deep copy constructor - returns a reference to the copied Vector

        Returns:
            Vector: the copied Vector
        """
        return Vector(
            *self.normal,
            self.origin,
            self.getColor(),
            self.thickness,
            self.coneRadius,
            self.coneHeight,
        )

    def transform(self, x2=1, y2=0, z2=0, xLam=None, yLam=None, zLam=None):
        """
        Transforms the Vector from its current state to a new (x2, y2, z2). It's
        possible to do this with lambda functions that define how the transformation
        occurs in time, but it's a bit finicky and not for beginners.

        Args:
            x2 (int, optional): new x-component of Vector. Defaults to 1.
            y2 (int, optional): new y-component of Vector. Defaults to 0.
            z2 (int, optional): new z-component of Vector. Defaults to 0.
            xLam (lambda, optional): x-lambda that defines transformation as a
            function of time. Defaults to None.
            yLam (lambda, optional): y-lambda that defines transformation as a
            function of time. Defaults to None.
            zLam (lambda, optional): z-lambda that defines transformation as a
            function of time. Defaults to None.
        """
        self.delete()
        self.__init__(
            x2,
            y2,
            z2,
            self.origin,
            self.objColor,
            self.thickness,
            self.coneRadius,
            self.coneHeight,
        )
    def init_transform(
        self, t0=0, tf=1, rate=EASE_IN_OUT, x2=1, y2=0, z2=0, x=None, y=None, z=None
    ):
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # if no lambdas specified, create a default linear scaling between normals
        ogAxis = mut.Vector(self.normal)
        newAxis = mut.Vector((x2, y2, z2))
        v = (newAxis - ogAxis) / (tf - t0)
        if x == None or y == None or z == None:

            def x(t):
                return ogAxis[0] + (t - t0) * v[0]

            def y(t):
                return ogAxis[1] + (t - t0) * v[1]

            def z(t):
                return ogAxis[2] + (t - t0) * v[2]

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append((x(tj), y(tj), z(tj)))
        return stack
    def update_transform(self, val, x2=1, y2=0, z2=0, x=None, y=None, z=None):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.transform(*val)

    def rotate(self, axis=(0, 0, 1), angle=0, angleDeg=False):
        """
        Rotations are done through a transform() implementation instead of the
        normal way of rotating objects. The reason for this is it easily keeps track
        of the components of the Vector.

        Args:
            axis (tuple, optional): axis of rotation. Defaults to (0, 0, 1).
            angle (float, optional): angle through which rotation should occur.
                Defaults to 0.
            angleDeg (bool, optional): whether or not angle is in degrees or radians.
                Defaults to False.

        Raises:
            CustomError: rotation axis must be non-zero.
            CustomError: rotation can't be a 180 degree flip because of indeterminate
                quaternion issues - if needed, just do two 90 degree flips.
        """
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a reasonable rotation axis to be passed in as a tuple"
            )
        if angleDeg:
            angle = angle * PI / 180
        # first, determine the new vector via quaternion
        q = mut.Quaternion(axis, angle)
        if q.magnitude == 0:
            raise CustomError(
                "Indeterminate Quaternion Rotation: make use of another rotation to interpolate between antiparallel states"
            )
        q.normalize()
        newVec = q @ (mut.Vector(self.normal))
        # now, just transform it
        self.transform(newVec[0], newVec[1], newVec[2])

    # need this functionality for situations like rotating after calling changeOriginTo()
    def superRotate(self, axis=(0, 0, 1), angle=0, angleDeg=False):
        """
        The previously defined rotate() function should be the standard way of doing
        it. However, if one wants to rotate the Vector after calling changeOriginTo(),
        the Blobject version of rotate() needs to be invoked.
        
        Args:
            axis (tuple, optional): axis of rotation. Defaults to (0, 0, 1).
            angle (float, optional): angle through which rotation should occur.
                Defaults to 0.
            angleDeg (bool, optional): whether or not angle is in degrees or radians.
                Defaults to False.
        """
        super().rotate(axis, angle, angleDeg)
    def init_superRotate(
        self, t0=0, tf=1, rate=EASE_IN_OUT, axis=(0, 0, 1), angle=0, angleDeg=False
    ):
        return super().init_rotate(t0, tf, rate, axis, angle, angleDeg)
    def update_superRotate(self, val, axis=(0, 0, 1), angle=0, angleDeg=False):
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.superRotate(axis, val, angleDeg)
