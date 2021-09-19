import bpy # pylint: disable=import-error
import mathutils as mut
import os
import sys
from collections import deque
from hashlib import sha256
from statistics import mean, mode
from constants import ORIGIN, C, SVG_DIR, D, BLACK, CustomError, EASE_IN_OUT,\
    FRAME_RATE, WHITE, Y, PI, RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE,\
    TEMPLATE_TEX_FILE_BODY
from blobjects.blobject import Blobject
from externals.bezier_interpolation import interpolate
from externals.blender_utils import selectOnly, computeQuaternion
from externals.iterable_utils import addition

class Tex(Blobject):
    def __init__(
        self,
        expression,
        scale=1,
        twistable=True,
        origin=ORIGIN,
        titleIn=False,
        f=None,
        render=None,
        xShift=None,
        yShift=None,
    ):
        """Tex object in UI.

        Args:
            expression (str): expression that's rendered in LaTeX, converted into an
                SVG, then shown in the UI.
            scale (float, optional): scale of Tex. Defaults to 1.
            twistable (bool, optional): whether it's 'twistable' or not. A good rule of
                thumb is to keep this to True when rotating Texs around in 3 dimensions
                and just leave it as False if only working with Texs in 2 dimensions.
                Defaults to True.
            origin (tuple, optional): origin of Tex. Defaults to ORIGIN.
            titleIn (bool, optional): whether or not the Tex should be rendered in via
                a title sequence. Defaults to False.
            f (Frame, optional): the Frame object needed to render a title sequence
                for the Tex if titleIn is True. Defaults to None.
            render (bool, optional): a forcing value for render if f.render is
                unsatisfactory. Defaults to None.
            xShift (float, optional): a forced x-shift if the automatic x-shift is
                unsatisfactory. Defaults to None.
            yShift (yShift, optional): a forced x-shift if the automatic x-shift is
                unsatisfactory. Defaults to None.

        Raises:
            CustomError: Frame() object must be passed in if titleIn is True
        """
        if f and render == None:
            render = f.render
        super().__init__()
        self.expression = expression
        self.hash = tex_hash(expression)
        self.morphPaths = []
        # deselect everything
        selectOnly([])
        svgFile = tex_to_svg_file(expression)
        # get objects before import
        names_pre_import = set([o.name for o in C.scene.objects])
        # import svg
        bpy.ops.import_curve.svg(filepath=os.path.join(SVG_DIR, svgFile))
        # get objects after import
        names_post_import = set([o.name for o in C.scene.objects])
        # differential objects are newly added objects
        new_object_names = names_post_import.difference(names_pre_import)
        self.name = [name for name in new_object_names]
        self.tampered = [False] * len(self.name)
        for name in new_object_names:
            o = C.scene.objects[name]
            o.select_set(True)
            C.view_layer.objects.active = o
        bpy.ops.transform.resize(
            value=(scale * 1000, scale * 1000, scale * 1000),
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
        bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
        # shift the entire expression into the center
        # first, grab the minimum and maximum location numbers
        minXLoc = sys.maxsize
        maxXLoc = -sys.maxsize
        minYLoc = sys.maxsize
        maxYLoc = -sys.maxsize
        self.xLocs = []
        self.yLocs = []
        for leName in new_object_names:
            xLoc = D.objects[leName].location[0]
            self.xLocs.append(xLoc)
            yLoc = D.objects[leName].location[1]
            self.yLocs.append(yLoc)
            if xLoc > maxXLoc:
                maxXLoc = xLoc
            if xLoc < minXLoc:
                minXLoc = xLoc
            if yLoc > maxYLoc:
                maxYLoc = yLoc
            if yLoc < minYLoc:
                minYLoc = yLoc
        self.minX = minXLoc
        self.minY = minYLoc
        self.maxX = maxXLoc
        self.maxY = maxYLoc
        # sort the names of the objects based on location
        self.xSortedNames = [
            x for _, x in sorted(zip(self.xLocs, self.name), key=lambda pair: pair[0])
        ]
        self.ySortedNames = [
            x for _, x in sorted(zip(self.yLocs, self.name), key=lambda pair: pair[0])
        ]
        # shift by the average x-location value
        if xShift:
            self.shift(xShift)
            self.xShift = xShift
        else:
            self.shift(-(maxXLoc + minXLoc) / 2)
            self.xShift = -(maxXLoc + minXLoc) / 2
        # move to the mode y-location value
        if yShift:
            self.shift(0, yShift)
            self.yShift = yShift
        else:
            try:
                self.shift(0, -mode(self.yLocs))
                self.yShift = -mode(self.yLocs)
            except:
                self.shift(0, -mean(self.yLocs))
                self.yShift = -mean(self.yLocs)
        # now set the origin of each curve in the Tex object to the origin
        if twistable:
            for name in new_object_names:
                o = C.scene.objects[name]
                o.select_set(True)
                C.view_layer.objects.active = o
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
        self.twistable = twistable
        self.scale = scale
        self.origin = ORIGIN
        self.shift(*origin)
        self.color(BLACK)
        if titleIn:
            # check for Frame() object
            if f == None:
                raise CustomError("Frame() object must be passed in if titleIn == True")
            self.titleSequenceIn(f, render=render)

    def cameraTrack(self):
        """
        Reorients the Tex so that it faces the camera.
        """
        # force the tex to be twistable in order to cameraTrack
        if not self.twistable:
            for name in self.name:
                o = C.scene.objects[name]
                o.select_set(True)
                C.view_layer.objects.active = o
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            self.twistable = True
        for name in self.name:
            obj = D.objects[name]
            obj.rotation_mode = "QUATERNION"
            # obj.rotation_quaternion = C.scene.camera.rotation_quaternion
            # twist label, so it's facing camera by its position
            loc = C.scene.camera.location
            o = self.origin
            connection = (loc[0] - o[0], loc[1] - o[1], loc[2] - o[2])
            quat = C.scene.camera.rotation_quaternion
            camNormal = quat @ mut.Vector((0, 0, 1))
            newQuat = computeQuaternion(camNormal, mut.Vector(connection))
            obj.rotation_quaternion = newQuat @ quat
    def init_cameraTrack(self, t0=0, tf=1, rate=EASE_IN_OUT):
        # never had an init_ and update_ not actually need a stack...
        # implementing a dummy stack as a poor man's fix for now
        t = interpolate(t0, tf, rate)
        t.pop(0)
        stack = deque()
        for _ in t:
            stack.append(0)
        return stack
    def update_cameraTrack(self, val):
        self.cameraTrack()

    def rescale(self, scaler=1):
        """
        Rescales the Tex. NOTE: only works for Tex not oriented in fancy directions.

        Args:
            scaler (float, optional): new scale of Tex object. Defaults to 1.
        """
        leColor = self.getColor()
        self.delete()
        self.__init__(self.expression, scaler, self.twistable, self.origin)
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

    def miniShift(self, name=None, morphShift=None):
        """
        A function that's needed for morphFrom(). I have never had to call this
        manually.

        Args:
            name (str, optional): the name of the Tex to be shifted. Defaults to None.
            morphShift (list, optional): list that defines the shift. Defaults to None.
        """
        selectOnly([name])
        # shift the object
        bpy.ops.transform.translate(
            value=morphShift,
            orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
            mirror=True,
        )
    def morphFrom(
        self, f=None, texObj=None, halfRuntime=1, rate=EASE_IN_OUT, render=None
    ):
        """
        A nifty function that morphs one Tex (texObj) into another (the current Tex).
        First, the common elements of each Tex are traced from one Tex object to this
        one. Then, the uncommon elements are title-sequenced in.

        Args:
            f (Frame, optional): Frame object needed for rendering the morph.
                Otherwise, there's no point. Defaults to None.
            texObj (Tex, optional): Original Tex object that this Tex is morphing from.
                Defaults to None.
            halfRuntime (float, optional): the runtime for half of the morph to take
                place. Half of the runtime is the shifts, the other half is the
                titleIn's. Defaults to 1.
            rate (tuple, optional): Bezier-curve defined rate. Defaults to EASE_IN_OUT.
            render (bool, optional): can force a render if f.render is False. Defaults
                to None.

        Raises:
            CustomError: texObj to morph from must be passed in
            CustomError: Frame object must be passed in
            CustomError: Neither Tex object can be a twistable object
            CustomError: Tex objects must have the same scale
        """
        # check for texObj
        if texObj == None:
            raise CustomError("texObj to morph from must be passed into this function")
        if f == None:
            raise CustomError("Frame object must be passed in")
        if render == None:
            render = f.render
        # check for twistability - do not allow morphing if it is twistable
        if self.twistable or texObj.twistable:
            raise CustomError("Neither Tex object can be a twistable object")
        # check for same scale
        if self.scale != texObj.scale:
            raise CustomError("Tex objects don't have the same scale")
        # check for similar curves
        self.morphPaths = []
        i = 0
        for name in self.name:
            nameSet = []
            # find a name in self.name which matches any name (set) in texObj.name
            for oldName in texObj.name:
                # check if names match
                if morphParser(oldName) == morphParser(name):
                    # add the old name into the nameset
                    nameSet.append(oldName)
            # now, choose the closest curve in nameSet to this curve
            if len(nameSet) == 0:
                self.morphPaths.append([0, 0, 0])
            else:
                minDistance = -1
                for newMini in nameSet:
                    newLocation = D.objects[name].location
                    oldLocation = D.objects[newMini].location
                    shiftPath = newLocation - oldLocation
                    if minDistance == -1:
                        minDistance = shiftPath.length
                        properMini = newMini
                    elif shiftPath.length < minDistance:
                        minDistance = shiftPath.length
                        properMini = newMini
                newLocation = D.objects[name].location
                oldLocation = D.objects[properMini].location
                shiftPath = newLocation - oldLocation
                shiftPath = [ai for ai in shiftPath]
                self.morphPaths.append(shiftPath)
                self.tampered[i] = True
                self.colorSubprocess(name, texObj.objColor)
            i += 1
        # now, time to actually shift the tampered
        # first, shift backwards
        for name, shiftAmount in zip(self.name, self.morphPaths):
            tempShift = tuple(-ai for ai in shiftAmount)
            # shift the untampered out-of-sight
            if tempShift == ORIGIN:
                tempShift = (100, 0, 0)
            self.miniShift(name, tempShift)
        # now shift to their correct spots with raw rendering and the correct rate
        t = interpolate(0, halfRuntime, rate)
        t = [i / halfRuntime for i in t]
        diff = [t[i + 1] - t[i] for i in range(len(t) - 1)]
        if render:
            f.start()
        numFrames = round(FRAME_RATE * halfRuntime)
        for i in range(numFrames):
            for name, shiftAmount in zip(self.name, self.morphPaths):
                tempShift = tuple(ai * diff[i] for ai in shiftAmount)
                self.miniShift(name, tempShift)
            if render:
                f.r()
        if render:
            f.stop()
        # now, undo the out-of-sight shift
        for name, shiftAmount in zip(self.name, self.morphPaths):
            tempShift = tuple(-ai for ai in shiftAmount)
            # shift the untampered back in sight
            if tempShift == ORIGIN:
                tempShift = (-100, 0, 0)
                self.miniShift(name, tempShift)
        # then, do a title sequence in
        self.titleSequenceIn(f, texObj.objColor, halfRuntime, render)

    # title sequence methods
    def titleSequenceIn(self, f=None, color=WHITE, runtime=2, render=None):
        """
        Flips the letters/characters of the Tex and colors them from black to color
        in a single animation.

        Args:
            f (Frame, optional): Frame object needed for rendering. Defaults to None.
            color (tuple, optional): 4-tuple that defines color of Tex. Defaults
                to WHITE.
            runtime (float, optional): runtime of animation. Defaults to 2.
            render (bool, optional): whether or not to force a render if f.render is
                False. Defaults to None.

        Raises:
            CustomError: Frame object must be passed in
        """
        # error checking
        if f == None:
            raise CustomError("Frame object must be passed in")
        if render == None:
            render = f.render
        self.color(BLACK)
        self.rotate(Y, PI / 2)
        f.play(
            [self.fade, self.rotate],
            [[color, True], [Y, -PI / 2]],
            tf=runtime,
            render=render,
        )
        # everything should be untampered now
        self.tampered = [False] * len(self.name)

    def titleIn(self, color=WHITE):
        """
        A more flexible version of titleSequenceIn() - allows calling in play() or
        multiplay(). This is also a non-breaking change.

        Args:
            color (tuple, optional): color for Tex to be faded into. Defaults to
                WHITE.
        """
        self.fade(color, True)
        # everything should be untampered now
        self.tampered = [False] * len(self.name)
    def init_titleIn(self, t0=0, tf=1, rate=EASE_IN_OUT, color=WHITE):
        self.color(BLACK)
        self.rotate(Y, PI / 2)
        fadeStack = self.init_fade(t0, tf, rate, color, True)
        rotateStack = self.init_rotate(t0, tf, rate, Y, -PI / 2)
        stack = deque()
        for i, colVal, rotVal in zip(range(len(rotateStack)), fadeStack, rotateStack):
            stack.append([i, colVal, rotVal])
        return stack
    def update_titleIn(self, val, color=WHITE):
        self.color(val[1])
        self.rotate(Y, val[2])
        # check if you're on the first value in the stack
        if val[0] == 0:
            # everything should be untampered now
            self.tampered = [False] * len(self.name)

    def titleSequenceOut(self, f=None, runtime=2, render=None):
        """Just an intuitive wrapper for fade() really...

        Args:
            f (Frame, optional): Frame object needed for rendering. Defaults to None.
            runtime (int, optional): runtime of animation. Defaults to 2.
            render (bool, optional): able to force a render if desired. Defaults
                to None.

        Raises:
            CustomError: Frame object must be passed in
        """
        # error checking
        if f == None:
            raise CustomError("Frame object must be passed in")
        if render == None:
            render = f.render
        f.play([self.fade], [[]], tf=runtime, render=render)
        self.delete()

    def titleSequence(self, f=None, runtime=2, render=None):
        """Just does a titleSequenceIn() followed by a titleSequenceOut().

        Args:
            f (Frame, optional): Frame object needed for rendering. Defaults to None.
            runtime (int, optional): runtime of animation. Defaults to 2.
            render (bool, optional): able to force a render if desired. Defaults
                to None.

        Raises:
            CustomError: Frame object must be passed in
        """
        # error checking
        if f == None:
            raise CustomError("frame object must be passed in")
        if render == None:
            render = f.render
        self.titleSequenceIn(f, runtime=runtime, render=render)
        self.titleSequenceOut(f, runtime=runtime, render=render)

    def flash(
        self,
        f=None,
        tinyRuntime=0.3,
        colors=[RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, WHITE],
        render=None,
    ):
        """
        Flashes a Tex object between a set of different colors at a tinyRuntime.

        Args:
            f (Frame, optional): Frame object needed for rendering. Defaults to None.
            tinyRuntime (float, optional): runtime of each color change in seconds.
                Defaults to 0.3.
            colors (list, optional): a list of colors to sequence through. Defaults
                to [RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, WHITE].
            render (bool, optional): whether or not to force a render. Defaults to
                None.

        Raises:
            CustomError: Frame object must be passed in
        """
        # error checking
        if f == None:
            raise CustomError("Frame object must be passed in")
        if render == None:
            render = f.render
        for col in colors:
            f.play([self.fade], [[col]], tf=tinyRuntime, render=render)

class Text(Tex):
    def __init__(
        self,
        expression,
        scale=1,
        twistable=True,
        origin=ORIGIN,
        titleIn=False,
        f=None,
        render=None,
    ):
        """
        Creates a Text object instead of Tex by rendering it outside of {align*} tags.

        Args:
            expression (str): text expression to be rendered.
            scale (float, optional): scale of Tex. Defaults to 1.
            twistable (bool, optional): whether it's 'twistable' or not. A good rule of
                thumb is to keep this to True when rotating Texs around in 3 dimensions
                and just leave it as False if only working with Texs in 2 dimensions.
                Defaults to True.
            origin (tuple, optional): origin of Tex. Defaults to ORIGIN.
            titleIn (bool, optional): whether or not the Tex should be rendered in via
                a title sequence. Defaults to False.
            f (Frame, optional): the Frame object needed to render a title sequence
                for the Tex if titleIn is True. Defaults to None.
            render (bool, optional): a forcing value for render if f.render is
                unsatisfactory. Defaults to None.
        """
        super().__init__(
            "\\end{align*}" + expression + "\\begin{align*}",
            scale,
            twistable,
            origin,
            titleIn,
            f,
            render,
        )

class TextHelvetica(Tex):
    def __init__(
        self,
        expression,
        scale=1,
        twistable=True,
        origin=ORIGIN,
        titleIn=False,
        f=None,
        render=None,
    ):
        """Just a Text object, but with a sans-serif Helvetica font.

        Args:
            expression (str): text expression to be rendered.
            scale (float, optional): scale of Tex. Defaults to 1.
            twistable (bool, optional): whether it's 'twistable' or not. A good rule of
                thumb is to keep this to True when rotating Texs around in 3 dimensions
                and just leave it as False if only working with Texs in 2 dimensions.
                Defaults to True.
            origin (tuple, optional): origin of Tex. Defaults to ORIGIN.
            titleIn (bool, optional): whether or not the Tex should be rendered in via
                a title sequence. Defaults to False.
            f (Frame, optional): the Frame object needed to render a title sequence
                for the Tex if titleIn is True. Defaults to None.
            render (bool, optional): a forcing value for render if f.render is
                unsatisfactory. Defaults to None.
        """
        super().__init__(
            "\\end{align*}{\\fontfamily{phv}\\selectfont "
            + expression
            + "}\\begin{align*}",
            scale,
            twistable,
            origin,
            titleIn,
            f,
            render,
        )

class TexManager(object):
    def __init__(self, frame, expression, origin=ORIGIN, scale=0.7, twistable=False):
        """
        An easy, intuitive way of managing many Tex objects, especially when creating
        derivations, lists, or something similar.

        Args:
            frame (Frame): Frame object needed for rendering.
            expression (str): expression of first Tex object.
            origin (tuple, optional): origin of first Tex object. Defaults to ORIGIN.
            scale (float, optional): scale of every Tex object. Defaults to 0.7.
            twistable (bool, optional): twistable attribute of every Tex object.
                Defaults to False.
        """
        self.noMorph = True
        self.texs = []
        self.f = frame
        self.scale = scale
        self.twistable = twistable
        self.texs.append(Tex(expression, scale, twistable, origin, True, self.f))

    def insert(
        self,
        expression,
        origin=ORIGIN,
        morphIdx=-2,
        scale=None,
        twistable=None,
        relative=True,
        runtime=2,
    ):
        """
        Function that inserts a Tex object with options to morph from any previous Tex
        or simply to just title-sequence in.

        Args:
            expression (str): Tex expression of new Tex object.
            origin (tuple, optional): if relative is True, this is a shift relative
                to the previous Tex object. If relative is False, this is an absolute
                origin. Defaults to ORIGIN.
            morphIdx (int, optional): the index of the Tex to morph this new Tex from.
                You can use TexManager.print() to see the indices of each Tex object.
                Alternatively, if you set this to False, it will simply title-sequence
                the new Tex in. Defaults to -2.
            scale (float, optional): scale of the new Tex object. Defaults to None,
                in which case it's the scale of the TexManager.
            twistable (bool, optional): whether or not the Tex is twistable. Defaults
                to None, in which case it's the twistable of the TexManager.
            relative (bool, optional): whether or not origin is relative to the
                previous Tex or absolute. Defaults to True, so relative.
            runtime (int, optional): the runtime of the morphing or title-sequence.
                Defaults to 2.

        Raises:
            CustomError: morphIdx must be an int or False
        """
        if scale == None:
            scale = self.scale
        if twistable == None:
            twistable = self.twistable
        if relative == True and len(self.texs) > 0:
            origin = addition(origin, self.texs[-1].origin)
        self.texs.append(Tex(expression, scale, twistable, origin))
        if type(morphIdx) is int:
            if self.noMorph and not self.f.render:
                self.texs[-1].color(WHITE)
            else:
                self.texs[-1].morphFrom(self.f, self.texs[morphIdx], runtime / 2)
        elif morphIdx == False:
            self.texs[-1].titleSequenceIn(self.f, runtime=runtime)
        else:
            raise CustomError("morphIdx must be an int or False")

    def shift(self, indices=True, amt=[1, 0, 0], runtime=2):
        """Shifts some or all of the Tex objects that are a part of the TexManager.

        Args:
            indices (list, optional): a list of the indices whose Tex's should shift.
                Alternatively, you can set this to True to shift all the Tex's.
                Defaults to True.
            amt (list, optional): a shift in list-form. Defaults to [1, 0, 0].
            runtime (int, optional): runtime of animation. Defaults to 2.
        """
        # default (True) would be for all of the texs
        if indices == True:
            indices = list(range(len(self.texs)))
        elif type(indices) is not list:
            indices = [indices]
        if type(amt[0]) is not list:
            amt = [amt]
        shiftTexs = []
        for idx in indices:
            shiftTexs.append(self.texs[idx])
        self.f.multiplay(shiftTexs, "shift", amt, tf=runtime)

    def fadeShift(self, indices=True, amt=[BLACK, 1, 0, 0], delete=False, runtime=2):
        """
        FadeShifts some or all of the Tex objects that are a part of the TexManager.

        Args:
            indices (list, optional): a list of the indices whose Tex's should
                fadeShift. Alternatively, you can set this to True to fadeShift all
                the Tex's. Defaults to True.
            amt (list, optional): a fadeShift in list-form. Defaults to
                [BLACK, 1, 0, 0].
            delete (bool, optional): whether or not to delete the chosen Tex's after
                fadeShifting them. Defaults to False.
            runtime (int, optional): runtime of animation. Defaults to 2.
        """
        # default (True) would be for all of the texs
        if indices == True:
            indices = list(range(len(self.texs)))
        elif type(indices) is not list:
            indices = [indices]
        if type(amt[0]) is not list:
            amt = [amt]
        shiftTexs = []
        for idx in indices:
            shiftTexs.append(self.texs[idx])
        self.f.multiplay(shiftTexs, "fadeShift", amt, tf=runtime)
        if delete:
            self.delete(indices)

    def print(self):
        """
        A simple function to print the indices of the Tex objects contained within
        the TexManager.
        """
        print("TEXMANAGER INDICES:")
        for i, tex in zip(range(len(self.texs)), self.texs):
            print(f"\t{i}: {tex.expression}")

    def delete(self, indices=[0]):
        """Deletes some or all of the Tex objects associated with the TexManager.

        Args:
            indices (list, optional): A list of Tex indices to delete. Defaults
                to [0].
        """
        if type(indices) is not list:
            indices = [indices]
        indices.sort()
        # delete objects
        for idx in indices:
            self.texs[idx].delete()
        # adjust the indices
        counter = 0
        for i in range(len(indices)):
            indices[i] -= counter
            counter += 1
        # remove indices
        for idx in indices:
            self.texs.pop(idx)

# necessary tex stuff below
# the following five functions are adapted from
# https://github.com/3b1b/manim
def tex_hash(expression):
    """Returns a truncated hash of an input expression.

    Args:
        expression (str): the expression that would be passed into a Tex object.

    Returns:
        str: 16-byte truncated hash of expression.
    """
    id_str = str(expression)
    hasher = sha256()
    hasher.update(id_str.encode())
    # truncating at 16 bytes for cleanliness
    # see "birthday paradox"
    # after roughly 10,000,000 SVG files (~10 GB) are generated,
    # the probability of collision is 3 in a million...
    return hasher.hexdigest()[:16]
def tex_to_svg_file(expression):
    """At a high level, renders a Tex document into an SVG file.

    Args:
        expression (str): the expression that would be passed into a Tex object.

    Returns:
        str: filename of rendered SVG.
    """
    # step 1
    tex_file = generate_tex_file(expression)
    # step 2
    dvi_file = tex_to_dvi(tex_file)
    # step 3
    svg_file = dvi_to_svg(dvi_file)
    # step 4
    delete_extras(expression)
    return svg_file
def generate_tex_file(expression):
    """Creates a Tex file out of a LaTeX expression. (step 1)

    Args:
        expression (str): LaTeX expression.

    Returns:
        str: Tex filename.
    """
    result = os.path.join(SVG_DIR, tex_hash(expression)) + ".tex"
    svgResult = os.path.join(SVG_DIR, tex_hash(expression)) + ".svg"
    if not os.path.exists(svgResult):
        print('Writing "%s" to %s' % ("".join(expression), result))
        new_body = TEMPLATE_TEX_FILE_BODY.replace("YOUR_TEXT_HERE", expression)
        with open(result, "w", encoding="utf-8") as outfile:
            outfile.write(new_body)
    return result
def tex_to_dvi(tex_file):
    """Creates a DVI file out of a Tex file. (step 2)

    Args:
        tex_file (str): Tex filename.

    Raises:
        CustomError: general error when Tex file can't be converted into DVI file.

    Returns:
        str: DVI filename.
    """
    result = tex_file.replace(".tex", ".dvi")
    svgResult = tex_file.replace(".tex", ".svg")
    if not os.path.exists(svgResult):
        commands = [
            "latex",
            "-interaction=batchmode",
            "-halt-on-error",
            '-output-directory="{}"'.format(SVG_DIR),
            '"{}"'.format(tex_file),
            ">",
            os.devnull,
        ]
        exit_code = os.system(" ".join(commands))
        if exit_code != 0:
            log_file = tex_file.replace(".tex", ".log")
            raise CustomError(
                ("Latex error converting to dvi. ") + "See log file at: %s" % log_file
            )
    return result
def dvi_to_svg(dvi_file):
    """
    Converts a dvi, which potentially has multiple slides, into a directory full of
    enumerated pngs corresponding with these slides. Returns a list of PIL Image
    objects for these images sorted as they were in the dvi. (step 3)

    Args:
        dvi_file (str): DVI filename.

    Returns:
        str: SVG filename.
    """
    result = dvi_file.replace(".dvi", ".svg")
    if not os.path.exists(result):
        commands = [
            "dvisvgm",
            '"{}"'.format(dvi_file),
            "-n",
            "-v",
            "0",
            "-o",
            '"{}"'.format(result),
            ">",
            os.devnull,
        ]
        os.system(" ".join(commands))
    return result

def delete_extras(expression):
    """Deletes all the unnecessary extras - I only need the svg. (step 4)

    Args:
        expression (str): original Tex expression
    """
    fileBeginning = os.path.join(SVG_DIR, tex_hash(expression))
    # check for each filetype
    if os.path.exists(fileBeginning + ".tex"):
        os.remove(fileBeginning + ".tex")
    if os.path.exists(fileBeginning + ".log"):
        os.remove(fileBeginning + ".log")
    if os.path.exists(fileBeginning + ".dvi"):
        os.remove(fileBeginning + ".dvi")
    if os.path.exists(fileBeginning + ".aux"):
        os.remove(fileBeginning + ".aux")

def morphParser(strToParse):
    """
    Parses out a non-unique name for individual character object types in LaTeX
    SVG objects. Need this for morphFrom().

    Args:
        strToParse (str): name of object in Blender UI.

    Raises:
        CustomError: precautionary check for too many splits (never been triggered).

    Returns:
        str: resultant number from name that identifies the character type.
    """
    # example: "g2-100.001" -> want "100" from that mix
    # split by "." first - don't care about trailing duplicate id
    firstSplit = strToParse.split(".")[0]
    # now split by "-"
    secondSplit = firstSplit.split("-")
    if len(secondSplit) > 1:
        secondSplit.pop(0)
    if len(secondSplit) != 1:
        raise CustomError(strToParse + " is too long. time to add a new case?")
    return secondSplit[-1]
