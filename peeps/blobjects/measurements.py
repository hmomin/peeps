import bpy
import mathutils as mut
import numpy as np
from collections import deque
from constants import C, ORIGIN, Y, PI, Z, D, BLACK, EASE_IN_OUT, X, CustomError
from blobjects.blobject import Blobject
from blobjects.shapes import Ball, Cylinder, Line
from externals.bezier_interpolation import interpolate
from externals.blender_utils import selectOnly

class Angle(Blobject):
    def __init__(self, centerDist=1, v1=(10, 0, 0), v2=(0, 10, 0), thickness=0.02):
        """
        Just a simple arc defined by three primary parameters. A circular arc is
        traced out from v1 to v2.

        Args:
            centerDist (int, optional): The arc's radius of curvature. Defaults to 1.
            v1 (tuple, optional): The initial direction the arc starts at. Defaults
                to (10, 0, 0).
            v2 (tuple, optional): The final direction the arc ends at. Defaults
                to (0, 10, 0).
            thickness (float, optional): Thickness of arc. Defaults to 0.02.
        """
        super().__init__()
        # determine angle between v1 and v2
        vec1 = mut.Vector(v1)
        vec2 = mut.Vector(v2)
        if vec1[2] == 0 and vec2[2] == 0:
            # preferred determination of angle if vectors are in 2D plane:
            angle = np.arctan2(vec2[1], vec2[0]) - np.arctan2(vec1[1], vec1[0])
            if angle < 0:
                angle += 2 * PI
        else:
            # actual shortest angle between the two 3D vectors
            angle = np.arccos(
                np.clip(vec1.dot(vec2) / (vec1.length * vec2.length), -1, 1)
            )
        # s = r*theta
        arcLength = centerDist * angle
        # note: weird hack here where i have to tune the cylinder height
        # too big (> ~10^-2) and the curve radius gets too large
        # too small (< 10^-4) and the curve is lopsided
        # need this cause deform mod was being dumb
        dh = 0.001
        c = Cylinder(radius=thickness, height=dh, origin=(0, dh / 2, 0))
        c.transform(Y)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        self.id = self.createID("arc")
        strI = self.stringID(self.id)
        self.name = ["arc" + strI]
        currObj = C.active_object
        currObj.name = self.name[0]
        # curve arc by adding loopcuts and a simple-deform bend
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
                "number_cuts": 50,
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
        # shift in the local y-axis away from center
        bpy.ops.transform.translate(
            value=(0, 0, centerDist), constraint_axis=(False, False, True), mirror=True
        )
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        # perform bend
        bpy.ops.object.modifier_add(type="SIMPLE_DEFORM")
        C.object.modifiers["SimpleDeform"].deform_method = "BEND"
        C.object.modifiers["SimpleDeform"].angle = arcLength / centerDist
        # normal transform
        self.normal = (-1, 0, 0)
        vec3 = vec1.cross(vec2)
        # fixer transform for indeterminate quaternion rotation or 180 degree arc
        if vec3[0] >= 0 and vec3[1] == 0 and vec3[2] == 0:
            self.transform(Z)
        if vec3.length > 0:
            self.transform((vec3[0], vec3[1], vec3[2]))
        # sloppy fix for angle being bigger than PI
        if angle > PI:
            self.rotate(angle=angle - PI)

class Distance(Blobject):
    def __init__(self, p1=ORIGIN, p2=ORIGIN, mid=0.02, ends=0.2, endsOn=True):
        """Generates a distance measurement object from p1 to p2.

        Args:
            p1 (tuple, optional): 3-tuple that defines position of first point.
                Defaults to ORIGIN.
            p2 (tuple, optional): 3-tuple that defines position of second point.
                Defaults to ORIGIN.
            mid (float, optional): thickness of middle portion of object.
                Defaults to 0.02.
            ends (float, optional): thickness of ends of object. Defaults to
                0.2.
            endsOn (bool, optional): Determines whether or not ends exist. If
                not, the entire object basically degenerates into a Line()
                with a change() function. Defaults to True.

        Raises:
            CustomError: [description]
        """
        super().__init__()
        # error checking
        p3 = mut.Vector((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
        if p3.length == 0:
            raise CustomError("Cannot determine length of cylinder - crashing...")
        # make a cylinder regularly oriented with height (p2.length - p1.length)
        c0 = Cylinder(radius=mid, height=p3.length)
        if endsOn:
            for h in [-p3.length / 2, p3.length / 2]:
                c = Cylinder(radius=ends, height=mid, origin=(0, 0, h))
                selectOnly([c0.name[0], c.name[0]])
                C.view_layer.objects.active = D.objects[c0.name[0]]
                bpy.ops.object.join()
                currObj = C.active_object
        else:
            currObj = C.active_object
        self.id = self.createID("dist")
        self.mid = mid
        self.ends = ends
        self.endsOn = endsOn
        strI = self.stringID(self.id)
        self.name = ["dist" + strI]
        currObj.name = self.name[0]
        self.shift(p1[0] + p3[0] / 2, p1[1] + p3[1] / 2, p1[2] + p3[2] / 2)
        self.transform((p3[0], p3[1], p3[2]))
        self.points = (p1, p2)
        self.color(BLACK)

    def change(self, p1=None, p2=None):
        """
        Allows you to change a Distance() from its original (p1, p2) combination to
        a new combination of (p1, p2).

        Args:
            p1 (tuple, optional): 3-tuple that defines new first point. Defaults
                to None.
            p2 (tuple, optional): 3-tuple that defines new second point. Defaults
                to None.
        """
        if p1 == None:
            p1 = self.points[0]
        if p2 == None:
            p2 = self.points[1]
        color = self.getColor()
        oldAlpha = self.currentAlpha
        self.delete()
        self.__init__(p1, p2, self.mid, self.ends, self.endsOn)
        self.color(color)
        if oldAlpha < 1:
            self.transparent(oldAlpha)
    def init_change(self, t0=0, tf=1, rate=EASE_IN_OUT, p1=ORIGIN, p2=ORIGIN):
        # error checking
        p3 = mut.Vector((p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]))
        if p3.length == 0:
            raise CustomError("Cannot determine length of cylinder - crashing...")
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # create a default linear scaling in distance object
        ogP1 = mut.Vector(self.points[0])
        ogP2 = mut.Vector(self.points[1])
        newP1 = mut.Vector(p1)
        newP2 = mut.Vector(p2)
        v1 = (newP1 - ogP1) / (tf - t0)
        v2 = (newP2 - ogP2) / (tf - t0)
        # define linear shifts
        def x1(t):
            return ogP1[0] + (t - t0) * v1[0]

        def y1(t):
            return ogP1[1] + (t - t0) * v1[1]

        def z1(t):
            return ogP1[2] + (t - t0) * v1[2]

        def x2(t):
            return ogP2[0] + (t - t0) * v2[0]

        def y2(t):
            return ogP2[1] + (t - t0) * v2[1]

        def z2(t):
            return ogP2[2] + (t - t0) * v2[2]

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append(((x1(tj), y1(tj), z1(tj)), (x2(tj), y2(tj), z2(tj))))
        return stack
    def update_change(self, val, p1=None, p2=None):
        # error checking
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.change(*val)

class Point(Blobject):
    def __init__(self, radius=0.3, origin=(1, 1, 0), line=True):
        """Creates a simple point in 3D-space out of a Ball().

        Args:
            radius (float, optional): radius of Point. Defaults to 0.3.
            origin (tuple, optional): origin of Point. Defaults to (1, 1, 0).
            line (bool, optional): determines whether or not a line extends from the
                point to the world origin. Defaults to True.
        """
        super().__init__()
        # create a ball and a line and join the two
        b = Ball(radius, origin)
        currObj = C.active_object
        if line and origin != ORIGIN:
            ell = Line(p2=origin)
            selectOnly([b.name[0], ell.name[0]])
            C.view_layer.objects.active = D.objects[b.name[0]]
            bpy.ops.object.join()
            currObj = C.active_object
            self.normal = origin
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        self.id = self.createID("point")
        strI = self.stringID(self.id)
        self.name = ["point" + strI]
        self.radius = radius
        self.origin = origin
        self.line = line
        currObj.name = self.name[0]

    def copy(self):
        """Deep copy constructor: returns a reference to the copied Point.

        Returns:
            Point: the copied Point.
        """
        leColor = self.getColor()
        p = Point(self.radius, self.origin, self.line)
        p.color(leColor)
        return p

class RightAngle(Blobject):
    def __init__(self, centerDist=1, thickness=0.02):
        """A simple right-angle object.

        Args:
            centerDist (float, optional): distance from each edge to the center of the
                angle. Defaults to 1.
            thickness (float, optional): thickness of the angle. Defaults to 0.02.
        """
        super().__init__()
        c0 = Cylinder(
            radius=thickness, height=centerDist, origin=(centerDist, centerDist / 2, 0)
        )
        c0.transform(Y)
        c1 = Cylinder(
            radius=thickness, height=centerDist, origin=(centerDist / 2, centerDist, 0)
        )
        c1.transform(X)
        selectOnly([c0.name[0], c1.name[0]])
        C.view_layer.objects.active = D.objects[c0.name[0]]
        bpy.ops.object.join()
        currObj = C.active_object
        self.id = self.createID("rightAngle")
        strI = self.stringID(self.id)
        self.name = ["rightAngle" + strI]
        currObj.name = self.name[0]
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
