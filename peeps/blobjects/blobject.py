import bpy # pylint: disable=import-error
import mathutils as mut
import numpy as np
import operator
from collections import deque
from constants import C, ORIGIN, CustomError, D, EASE_IN_OUT, PI, WHITE,\
    OBJECT_COUNTER, BLACK
from externals.blender_utils import selectOnly, computeQuaternion
from externals.bezier_interpolation import interpolate, getInterpolatedColors
from externals.iterable_utils import mag

class Blobject(object):
    """
    The Blobject is the super-class for all of the subclass objects defined below.
    It's designed to provide transform, shift, rotate (TSR) and other methods common
    to all of these objects. Any object that wishes to make use of its own TSR, etc.
    methods should have its own implementation of T, S, R, or whatever and it will
    completely override the Blobject definition. Each object should really make use of
    its own __init__ however, since each object has a different instantiation process.
    """

    def __init__(self):
        """
        Blobject constructor - called as a first for every object that inherits from
        Blobject.
        """
        self.normal = (0, 0, 1)
        self.origin = ORIGIN
        self.name = []
        self.tampered = []
        self.texNames = []
        self.isTransparent = False
        self.currentAlpha = 1

    def transform(self, newNormal=ORIGIN, x=None, y=None, z=None):
        """
        Transforms from an original normal to a new normal. Highly useful when
        determining the actual rotations can be hazy.

        Args:
            newNormal (tuple, optional): Defines the normal to be rotated to. Defaults
                to ORIGIN.
            x (lambda, optional): Defines x-lambda function that specify how the
                transformation happens in a timed animation. Defaults to None.
            y (lambda, optional): Defines y-lambda function that specify how the
                transformation happens in a timed animation. Defaults to None.
            z (lambda, optional): Defines z-lambda function that specify how the
                transformation happens in a timed animation. Defaults to None.

        Raises:
            CustomError: requires non-zero newNormal.
        """
        # error checking
        if newNormal == ORIGIN:
            raise CustomError(
                "Calling transform() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        selectOnly(self.name)
        for name in self.name:
            obj = D.objects[name]
            # define new vector
            ogAxis = mut.Vector(self.normal)
            newAxis = mut.Vector(newNormal)
            # determine quaternions
            q1 = computeQuaternion(ogAxis, newAxis)
            # perform quaternion rotation
            obj.rotation_mode = "QUATERNION"
            obj.rotation_quaternion = q1 @ obj.rotation_quaternion
        # reset normal
        self.normal = newNormal
    def init_transform(
        self, t0=0, tf=1, rate=EASE_IN_OUT, newNormal=ORIGIN, x=None, y=None, z=None
    ):
        """
        Every "init_..." function is the starting point of an animation. A stack is
        defined in an "init_..." function that is then traversed through with the
        "update_..." functions on each frame.

        Args:
            t0 (int, optional): Starting time of animation (in seconds). Defaults to 0.
            tf (int, optional): Ending time of animation (in seconds). Defaults to 1.
            rate (tuple, optional): Bezier-defined rate. Defaults to EASE_IN_OUT.

        Returns:
            deque: the interpolation stack to be traversed through on each call of
            "update_..."
        """
        # error checking
        if newNormal == ORIGIN:
            raise CustomError(
                "Calling transform() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # if no lambdas specified, create a default linear scaling between normals
        ogAxis = mut.Vector(self.normal)
        newAxis = mut.Vector(newNormal)
        v = (newAxis - ogAxis) / (tf - t0)
        if x == None or y == None or z == None:

            def x(t):  # pylint: disable=function-redefined
                return ogAxis[0] + (t - t0) * v[0]

            def y(t):  # pylint: disable=function-redefined
                return ogAxis[1] + (t - t0) * v[1]

            def z(t):  # pylint: disable=function-redefined
                return ogAxis[2] + (t - t0) * v[2]

        stack = deque()
        t.reverse()
        for tj in t:
            stack.append((x(tj), y(tj), z(tj)))
        return stack
    def update_transform(self, val, newNormal=ORIGIN, x=None, y=None, z=None):
        """
        Every "update_..." method defines how the animation evolves in time. Tiny
        chunks of rotation/shift are popped off the interpolation stack from
        "init_..." and used to update each individual frame.

        Args:
            val: The value popped off of the interpolation stack. Usually, it is simply
                used to call the original function, but sometimes special constraints
                are required, hence the need for an "update_..." function separate
                from the original.

        Raises:
            CustomError: val must be passed in from the interpolation stack.
        """
        # error checking
        if newNormal == ORIGIN:
            raise CustomError(
                "Calling transform() requires a new non-zero direction tuple to be passed in as newNormal"
            )
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        self.transform(val)

    def rotate(self, axis=(0, 0, 1), angle=0, angleDeg=False):
        """
        Rotates about an axis via some angle, by computing the relevant quaternion
        associated with such a rotation and appending it to the object's current
        quaternion.

        Args:
            axis (tuple, optional): Axis about which rotation occurs. Defaults to
                (0, 0, 1).
            angle (float, optional): Angle of rotation in radians (or degrees if angleDeg
                is True). Defaults to 0.
            angleDeg (bool, optional): Defines whether angles are in degrees. Defaults
                to False.

        Raises:
            CustomError: requires non-zero rotation axis
            CustomError: indeterminate quaternion error usually occurs in flipping
                180 degrees. There are separate checks for this for example in the
                Vector() functions.
        """
        # error checking
        if axis == ORIGIN:
            raise CustomError(
                "Calling rotate() requires a reasonable rotation axis to be passed in as a tuple"
            )
        if angleDeg:
            angle = angle * PI / 180
        # change axis to be normalized
        axis = tuple([i/mag(axis) for i in axis])
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
            # only rotate if untampered
            if len(self.tampered) > 0 and self.tampered[i]:
                continue
            for name in self.texNames:
                self.colorSubprocess(name, WHITE)
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

    def shift(self, x=0, y=0, z=0, xLam=None, yLam=None, zLam=None):
        """
        General shift function applied to an object.

        Args:
            x (int, optional): Amount to shift in x-direction. Defaults to 0.
            y (int, optional): Amount to shift in y-direction. Defaults to 0.
            z (int, optional): Amount to shift in z-direction. Defaults to 0.
            xLam (lambda, optional): Defines lambda function through which shift
                occurs. Defaults to None.
            yLam (lambda, optional): Defines lambda function through which shift
                occurs. Defaults to None.
            zLam (lambda, optional): Defines lambda function through which shift
                occurs. Defaults to None.
        """
        selectOnly(self.name)
        # shift the object
        bpy.ops.transform.translate(
            value=(x, y, z),
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
        self.origin = tuple(map(operator.add, self.origin, (x, y, z)))
    def init_shift(
        self,
        t0=0,
        tf=1,
        rate=EASE_IN_OUT,
        x=0,
        y=0,
        z=0,
        xLam=None,
        yLam=None,
        zLam=None,
    ):
        t = interpolate(t0, tf, rate)
        t.pop(0)
        stack = deque()
        # do a simple linear shift...
        if xLam == None or yLam == None or zLam == None:
            xDiffs = np.diff(interpolate(0, x, rate, numIntervals=len(t))).tolist()
            yDiffs = np.diff(interpolate(0, y, rate, numIntervals=len(t))).tolist()
            zDiffs = np.diff(interpolate(0, z, rate, numIntervals=len(t))).tolist()
            xDiffs.reverse()
            yDiffs.reverse()
            zDiffs.reverse()
            for xVal, yVal, zVal in zip(xDiffs, yDiffs, zDiffs):
                stack.append((xVal, yVal, zVal))
            return stack
        # ... unless lambdas specified, in which case, apply the shift along the lambda
        else:
            t.reverse()
            for tj in t:
                stack.append((xLam(tj), yLam(tj), zLam(tj)))
            return stack
    def update_shift(self, val, x=0, y=0, z=0, xLam=None, yLam=None, zLam=None):
        if val is None:
            raise CustomError(
                "val must be specified and passed into update_transform()"
            )
        if xLam != None and yLam != None and zLam != None:
            shifties = [vali - origi for vali, origi in zip(val, self.origin)]
            self.shift(shifties[0], shifties[1], shifties[2])
        else:
            self.shift(val[0], val[1], val[2])

    def colorSubprocess(self, someName, theColor):
        """
        Applies a coloring to a single part of some object if it contains multiple parts.

        Args:
            someName (str): the name of the subpart of the object to be colored.
            theColor (tuple): tuple of length 4 which defines the RGBA color.
        """
        selectOnly([someName])
        C.view_layer.objects.active = D.objects[someName]
        ob = C.active_object
        mat = D.materials.get(someName)
        # if no material, make it
        if mat is None:
            mat = D.materials.new(name=someName)
        # assign mat to object
        if ob.data.materials:
            # assign to first material slot
            ob.data.materials[0] = mat
        else:
            # no slots
            ob.data.materials.append(mat)
        # use nodes
        C.object.active_material.use_nodes = True
        mat = C.object.material_slots[C.active_object.name]
        mat.material.node_tree.nodes["Principled BSDF"].inputs[
            "Emission"
        ].default_value = theColor

    def color(self, theColor=WHITE, ignoreTampered=False):
        """
        General coloring of an object.

        Args:
            theColor (tuple, optional): tuple of length 4 that defines RGBA of color.
                Defaults to WHITE.
            ignoreTampered (bool, optional): necessary for Tex coloring. Defaults to
                False.
        """
        if hasattr(self, "texNames"):
            for name in self.texNames:
                self.colorSubprocess(name, theColor)
        i = -1
        for leName in self.name:
            i += 1
            if len(self.tampered) > 0 and self.tampered[i] and not ignoreTampered:
                continue
            self.colorSubprocess(leName, theColor)
        self.objColor = theColor
    def init_color(
        self, t0=0, tf=1, rate=EASE_IN_OUT, theColor=WHITE, ignoreTampered=False
    ):
        colors = getInterpolatedColors(t0, tf, self.getColor(), theColor, rate)
        stack = deque()
        colors.reverse()
        for var in colors:
            stack.append(var[1])
        return stack
    def update_color(self, val, theColor=WHITE, ignoreTampered=False):
        if val is None:
            raise CustomError("val must be specified and passed into update_color()")
        self.color(val)

    def fade(self, color=(-1, -1, -1, 1), ignoreTampered=False):
        """Fade from current color to color

        Args:
            color (tuple, optional): Color to be faded into. Defaults to
                (-1, -1, -1, 1).
            ignoreTampered (bool, optional): Necessary for proper Tex coloring.
                Defaults to False.
        """
        if color == (-1, -1, -1, 1):
            color = self.getOppositeColor()
        # wrapper for color
        theColor = color
        self.color(theColor, ignoreTampered)
    def init_fade(
        self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, 1), ignoreTampered=False
    ):
        if color == (-1, -1, -1, 1):
            color = self.getOppositeColor()
        return self.init_color(t0, tf, rate, color)
    def update_fade(self, val, color=(-1, -1, -1, 1), ignoreTampered=False):
        self.update_color(val)

    def fadeShift(self, color=(-1, -1, -1, -1), x=0, y=0, z=0):
        """
        Literally what the name implies: fades into a color while shifting by
        (x, y, z).

        Args:
            color (tuple, optional): Color to fade into. Defaults to
                (-1, -1, -1, -1).
            x (int, optional): Value to shift in the x-direction. Defaults to 0.
            y (int, optional): Value to shift in the y-direction. Defaults to 0.
            z (int, optional): Value to shift in the z-direction. Defaults to 0.

        Raises:
            CustomError: requires color to be a tuple
        """
        # error checking for color
        if type(color) is not tuple:
            raise CustomError("fadeShift() error: color must be a tuple")
        self.fade(color)
        self.shift(x, y, z)
    def init_fadeShift(
        self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, 1), x=0, y=0, z=0
    ):
        # error checking for color
        if type(color) is not tuple:
            raise CustomError("fadeShift() error: color must be a tuple")
        if color == (-1, -1, -1, 1):
            color = self.getOppositeColor()
        colors = getInterpolatedColors(t0, tf, self.getColor(), color, rate)
        colors.reverse()
        t = interpolate(t0, tf, rate)
        t.pop(0)
        # do a simple linear shift...
        xDiffs = np.diff(interpolate(0, x, rate, numIntervals=len(t))).tolist()
        yDiffs = np.diff(interpolate(0, y, rate, numIntervals=len(t))).tolist()
        zDiffs = np.diff(interpolate(0, z, rate, numIntervals=len(t))).tolist()
        xDiffs.reverse()
        yDiffs.reverse()
        zDiffs.reverse()
        stack = deque()
        # append fade and shift vals to stack
        for var, xVal, yVal, zVal in zip(colors, xDiffs, yDiffs, zDiffs):
            stack.append([var[1], (xVal, yVal, zVal)])
        return stack
    def update_fadeShift(self, val, color=(-1, -1, -1, 1), x=0, y=0, z=0):
        self.fade(val[0])
        self.shift(*val[1])

    def fadeLeft(self, color=(-1, -1, -1, -1), dist=0):
        self.fadeShift(color, -dist)
    def init_fadeLeft(
        self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, -1), dist=0
    ):
        return self.init_fadeShift(t0, tf, rate, color, -dist)
    def update_fadeLeft(self, val, color=(-1, -1, -1, -1), dist=0):
        self.update_fadeShift(val, color, -dist)

    def fadeRight(self, color=(-1, -1, -1, -1), dist=0):
        self.fadeShift(color, dist)
    def init_fadeRight(
        self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, -1), dist=0
    ):
        return self.init_fadeShift(t0, tf, rate, color, dist)
    def update_fadeRight(self, val, color=(-1, -1, -1, -1), dist=0):
        self.update_fadeShift(val, color, dist)

    def fadeUp(self, color=(-1, -1, -1, -1), dist=0):
        self.fadeShift(color, 0, dist)
    def init_fadeUp(self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, -1), dist=0):
        return self.init_fadeShift(t0, tf, rate, color, 0, dist)
    def update_fadeUp(self, val, color=(-1, -1, -1, -1), dist=0):
        self.update_fadeShift(val, color, 0, dist)

    def fadeDown(self, color=(-1, -1, -1, -1), dist=0):
        self.fadeShift(color, 0, -dist)
    def init_fadeDown(
        self, t0=0, tf=2, rate=EASE_IN_OUT, color=(-1, -1, -1, -1), dist=0
    ):
        return self.init_fadeShift(t0, tf, rate, color, 0, -dist)
    def update_fadeDown(self, val, color=(-1, -1, -1, -1), dist=0):
        self.update_fadeShift(val, color, 0, -dist)

    def transparent(self, alpha=1, ignoreTampered=False):
        """
        Makes an object transparent by some amount alpha. Alpha of 1 is totally
        opaque and alpha of 0 is totally transparent, i.e. completely dark and
        undetectable in the black scene. Balance between 0 and 1 is key.

        Args:
            alpha (int, optional): Alpha transparency. Defaults to 1.
            ignoreTampered (bool, optional): Necessary for Tex coloring. Defaults
                to False.
        """
        if hasattr(self, "texNames"):
            for name in self.texNames:
                self.transparentSubprocess(name, alpha)
        i = -1
        for leName in self.name:
            i += 1
            if len(self.tampered) > 0 and self.tampered[i] and not ignoreTampered:
                continue
            self.transparentSubprocess(leName, alpha)
        self.isTransparent = True
        self.currentAlpha = alpha
    def init_transparent(
        self, t0=0, tf=2, rate=EASE_IN_OUT, alpha=1, ignoreTampered=False
    ):
        timeVals = interpolate(t0, tf, rate)
        timeVals.pop(0)
        alphaValues = interpolate(self.currentAlpha, alpha, rate, len(timeVals))
        alphaValues.pop(0)
        stack = deque()
        alphaValues.reverse()
        for val in alphaValues:
            stack.append(val)
        return stack
    def update_transparent(self, val, alpha=1, ignoreTampered=False):
        self.transparent(val, ignoreTampered)

    def transparentSubprocess(self, someName, alpha):
        """Applies a transparency to a subpart of an object.

        Args:
            someName (str): the name of the subpart in Blender UI to which
                transparency must be applied.
            alpha (int): alpha value between 0 and 1, with 0 being totally
                transparent and 1 being totally opaque.
        """
        selectOnly([someName])
        C.view_layer.objects.active = D.objects[someName]
        ob = C.active_object
        mat = D.materials.get(someName)
        # if no material, make it
        if mat is None:
            mat = D.materials.new(name=someName)
        # assign mat to object
        if ob.data.materials:
            # assign to first material slot
            ob.data.materials[0] = mat
        else:
            # no slots
            ob.data.materials.append(mat)
        # use nodes
        C.object.active_material.use_nodes = True
        mat = C.object.material_slots[C.active_object.name]
        C.object.active_material.blend_method = "BLEND"
        # print(mat.material.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value)
        mat.material.node_tree.nodes["Principled BSDF"].inputs[
            "Alpha"
        ].default_value = alpha

    def changeOriginTo(self, x=0, y=0, z=0):
        """
        Changes the origin of an object to any (x, y, z) in space without actually
        shifting/reorienting the object. Considering rotate() rotates an object about
        its origin, this function is *very* useful.

        Args:
            x (int, optional): x-value of new origin. Defaults to 0.
            y (int, optional): y-value of new origin. Defaults to 0.
            z (int, optional): z-value of new origin. Defaults to 0.
        """
        # shift cursor to location
        C.scene.cursor.location = (x, y, z)
        for name in self.name:
            selectOnly(name)
            # shift object origin to cursor
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        # do it for texNames too
        for name in self.texNames:
            selectOnly(name)
            # shift object origin to cursor
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")
        # send 3D cursor back to origin
        C.scene.cursor.location = ORIGIN

    def delete(self):
        """
        Deletes an object from the UI and Blender memory. Necessary to free up
        space, as having many objects in the UI is the primary thing that slows
        down scripts in my experience.
        """
        # delete object's components in UI
        for stringy in self.name:
            D.objects.remove(D.objects[stringy], do_unlink=True)
        # find any dangling collections and delete them too
        for c in D.collections:
            if len(c.objects.values()) == 0:
                D.collections.remove(c)
        # delete dangling meshes, materials, lights, textures, curves, cameras, images
        for block in D.meshes:
            if block.users == 0:
                D.meshes.remove(block)
        for block in D.materials:
            if block.users == 0:
                D.materials.remove(block)
        for block in D.lights:
            if block.users == 0:
                D.lights.remove(block)
        for block in D.textures:
            if block.users == 0:
                D.textures.remove(block)
        for block in D.images:
            if block.users == 0:
                D.images.remove(block)
        for block in D.curves:
            if block.users == 0:
                D.curves.remove(block)
        for block in D.cameras:
            if block.users == 0:
                D.cameras.remove(block)
        # remove materials again - in case curves had materials
        for block in D.materials:
            if block.users == 0:
                D.materials.remove(block)

    def createID(self, str):
        """
        ID of an object - based on the global OBJECT_COUNTER, which counts upward
        to infinity.

        Args:
            str (str): No idea what this is for (!)

        Returns:
            int: the numerical ID of the object - also happens to be the global
                OBJECT_COUNTER.
        """
        # a simple counter shall suffice.
        global OBJECT_COUNTER
        OBJECT_COUNTER += 1
        return OBJECT_COUNTER

    def stringID(self, i):
        """
        String representation of an object's ID with 8 digits. I've never had
        anywhere remotely near 99 million objects generated in a script, so 8
        digits is plenty for me, but in principle, you can always change the 8
        to be a larger number... just not too large...

        Args:
            i (int): the ID for which a string is generated

        Returns:
            str: string representation of ID. Example: 34 becomes ".00000034"
        """
        return "." + str(i).zfill(8)

    def getOppositeColor(self):
        """
        Needed for determining the difference between light (any color) and
        dark (totally black).

        Returns:
            tuple: opposite color of object.
        """
        if self.getColor() == BLACK:
            return WHITE
        else:
            return BLACK

    def getColor(self):
        """
        Returns the current color of the object.

        Returns:
            tuple: current color of object.
        """
        if hasattr(self, "objColor"):
            return self.objColor
        for leName in self.name:
            selectOnly([leName])
            C.view_layer.objects.active = D.objects[leName]
            mat = D.materials.get(leName)
            # if no material, it's (probably?) black
            if mat is None:
                return BLACK
            else:
                mat = C.object.material_slots[C.active_object.name]
                leColor = (
                    mat.material.node_tree.nodes["Principled BSDF"]
                    .inputs["Emission"]
                    .default_value
                )
                return tuple(leColor[i] for i in (0, 1, 2, 3))
