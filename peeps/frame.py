import bpy
import os
import mathutils as mut
import time
from pathlib import Path
from contextlib import contextmanager
from subprocess import call
from constants import OUT_DIR, CustomError, FRAME_RATE, C, D, EASE_IN_OUT, LINEAR,\
    ORIGIN, BLACK, ev
from blobjects.scene import Camera
from externals.bezier_interpolation import interpolate
from externals.glow_utils import toggleGlow
from externals.iterable_utils import flatten
from externals.miscellaneous import timeFormatter

class Frame(object):
    def __init__(self, num=0, name="temp", render=True):
        """Constructor for Frame object - only one is really needed per script.

        Args:
            num (int, optional): The number that frames start at. Defaults to 0.
            name (str, optional): Name associated with Frame object. The name becomes
                the folder name for the output images/movies. Defaults to 'temp'.
            render (bool, optional): Determines whether or not to render images/movies.
                Defaults to True.
        """
        self.num = num
        self.sceneEnds = []
        self.startFrame = -1
        # fix for self.name
        if name[-3:] == ".py":
            self.name = os.path.basename(name)[:-3]
        else:
            self.name = name
        self.render = render
        self.file = ""
        newPath = os.path.join(OUT_DIR, name)
        if not os.path.exists(newPath):
            Path(newPath).mkdir(parents=True, exist_ok=True)

    def temporaryRender(self):
        """
        Creates a temporary render of the current scene. Useful for seeing what a
        scene would actually look like in png/mp4 format, rather than in Blender UI.
        """
        oldNum = self.num
        self.num = 900000
        while not self.checkRender():
            self.num += 1
        self.r()
        self.num = oldNum

    @contextmanager
    def video(self):
        """
        Context manager for video creation. Called using syntax such as the following
        (just renders the current scene for 100 frames into a video):

        with f.video() as rend:
            for _ in range(100):
                rend()

        Yields:
            function: renders out images if self.render is True.
        """
        # enter context manager
        try:
            if self.render:
                self.start()
            yield self.rYield
        # exit context manager
        finally:
            if self.render:
                self.stop()

    def rYield(self):
        """
        Only useful for the video context manager - not meant to be directly called.
        """
        if self.render:
            self.r()
        else:
            self.num += 1

    def start(self):
        """
        Starts a video process. From here, use self.r() to generate frames of the video.
        Use self.stop() to stop the video and concatenate the frames into a video.

        Raises:
            CustomError: cannot start a video in the middle of another video.
        """
        if self.startFrame == -1:
            self.startFrame = self.num
        else:
            raise CustomError("Cannot start video in the middle of another video")

    def stop(self):
        """
        Stops a video process and concatenates the pngs from Blender into a video
        using FFMPEG.

        Raises:
            CustomError: self.start() must have been called before this function is
                called.
            CustomError: FFMPEG-specific errors - meant to break everything if an error
                occurs and see what needs to be fixed.
        """
        firstFrame = self.startFrame
        if firstFrame == -1:
            raise CustomError("There is no video to stop")
        # only call ffmpeg if video doesn't exist
        elif not os.path.isfile(
            os.path.join(
                OUT_DIR, self.name, "img" + self.getFrameStr(firstFrame) + ".mp4"
            )
        ) and not os.path.isfile(
            os.path.join(
                OUT_DIR,
                self.name,
                self.file + "_" + self.getFrameStr(firstFrame) + ".mp4",
            )
        ):
            fileName = "img" + self.getFrameStr(firstFrame) + ".mp4"
            returnCode = call(
                [
                    "ffmpeg",
                    "-s",
                    "1920x1080",
                    "-pix_fmt",
                    "rgba",
                    "-r",
                    str(FRAME_RATE),
                    "-start_number",
                    str(firstFrame),
                    "-i",
                    os.path.join(OUT_DIR, self.name, "img%6d.png"),
                    "-vf",
                    "scale=in_color_matrix=bt601:out_color_matrix=bt709",
                    "-colorspace",
                    "bt709",
                    "-an",
                    "-loglevel",
                    "error",
                    "-vcodec",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    os.path.join(OUT_DIR, self.name, fileName),
                ]
            )
            # delete unnecessary images
            if returnCode == 0:
                for i in range(firstFrame, self.num):
                    lePath = os.path.join(
                        OUT_DIR, self.name, "img" + self.getFrameStr(i) + ".png"
                    )
                    if os.path.isfile(lePath):
                        os.remove(lePath)
            else:
                raise CustomError("FFMPEG error code " + str(returnCode))
        self.startFrame = -1
        # create one last image for extending purposes in video-editing software
        self.r()

    def r(self, justCheck=False):
        """
        Renders out a still (png) that will probably be concatenated with other
        stills into a video.

        Args:
            justCheck (bool, optional): If True, no pngs are rendered out. Instead,
                the function will just check if a png *would* be rendered out, since
                pngs are never over-written. Defaults to False.

        Returns:
            bool: Used to gauge whether or not a png will actually be rendered or not.
        """
        # don't render if a video has been started and the video exists
        # or if the image to render exists
        if (
            self.startFrame != -1
            and (
                os.path.isfile(
                    os.path.join(
                        OUT_DIR,
                        self.name,
                        "img" + self.getFrameStr(self.startFrame) + ".mp4",
                    )
                )
                or os.path.isfile(
                    os.path.join(
                        OUT_DIR,
                        self.name,
                        self.file + "_" + self.getFrameStr(self.startFrame) + ".mp4",
                    )
                )
            )
        ) or os.path.isfile(
            os.path.join(OUT_DIR, self.name, "img" + self.getFrameStr() + ".png")
        ):
            if not justCheck:
                self.num += 1
            return False
        elif not justCheck:
            scene = C.scene
            scene.render.image_settings.file_format = "PNG"
            scene.render.image_settings.compression = 0
            # bit-depth: controls the bit-depth ("color-depth") of the rendered images
            # 16-bit: 15.8 MB file
            # 8-bit: 7.92 MB file, so half as large
            # see this excellent video: https://youtu.be/Y-wSHpNJs-8
            scene.render.image_settings.color_depth = "8"
            scene.render.resolution_x = 1920
            scene.render.resolution_y = 1080
            scene.render.resolution_percentage = 100
            scene.render.filepath = os.path.join(
                OUT_DIR, self.name, "img" + self.getFrameStr() + ".png"
            )
            bpy.ops.render.render(write_still=True)
            self.num += 1
        return True

    def checkRender(self):
        # just a more intuitive alias to self.r(justCheck=True)
        return self.r(True)

    def getFrameStr(self, num=-1):
        """
        Determines the string representation of the image number to be generated.
        Example: if self.num is 45, then the image saved will be 'img000045.png'

        Args:
            num (int, optional): Determines the number to be used. Defaults to -1,
                in which case self.num is used.

        Raises:
            CustomError: negative frame numbers are not permitted

        Returns:
            str: string representation of the number padded with zeros in front.
        """
        if num == -1:
            num = self.num
        elif num < 0:
            raise CustomError("You've got a negative frame number?")
        return str(num).zfill(6)

    def play(
        self,
        funcs,
        args=None,
        t0=0,
        tf=2,
        rate=EASE_IN_OUT,
        render=None,
        testRender=False,
    ):
        """
        A more powerful version of the video() context manager. While video() allows
        you control over what happens on every single frame, play() allows you to
        specify animation types in advance (like shift, rotate, etc.) to avoid working
        with individual frames.

        Args:
            funcs (list): a list of all the functions to be called. Example:
                [ball.shift, text.rotate, vec.fadeShift]
            args (list[list], optional): a list of lists of arguments. Each list
                within args will map to its corresponding function call. Example:
                [[3], [Z, PI], [BLACK, 5]] using the funcs example will shift ball
                by 3 in the x-direction, rotate text about the Z axis by an angle of
                PI radians, and fadeShift vec to BLACK and by 5 units in the
                x-direction. If args is not as long as funcs, the last list in args
                will be applied to the remaining functions in funcs. Defaults to None.
            t0 (int, optional): Only needed for backwards compatibility. You would
                never really need to change this. Defaults to 0.
            tf (int, optional): If t0 is 0, tf is the amount of time the animation
                runs for in seconds. Defaults to 2.
            rate (tuple, optional): Bezier-determined rate to use. Defaults to
                EASE_IN_OUT.
            render (bool, optional): Determines whether or not to render out the video.
                Defaults to None.
            testRender (bool, optional): Allows one to see the final state of an
                animation in the UI exactly as it would be rendered in a movie. Slows
                things down, but very useful when debugging... Defaults to False.

        Raises:
            CustomError: requires funcs and args to be lists
        """
        # check for render
        if render == None:
            render = self.render
        # adjust for args not being passed in - use empty arguments for each function
        if args == None:
            args = []
        if args == []:
            args.append([])
        while len(args) < len(funcs):
            args.append(args[-1])
        # first, check to make sure funcs and args are lists
        if type(funcs) is not list or type(args) is not list:
            raise CustomError(
                "funcs and args must be lists in order to be passed into play()"
            )
        # just call the raw function if not rendering (doesn't work with lambdas though!)
        # if using lambdas, pass in "testRender=True"
        if not render and not testRender:
            for fun, vars in zip(funcs, args):
                fun(*vars)
            # fix for f.num
            if render != False:
                self.num += (tf - t0) * FRAME_RATE
        else:
            # determine the init and update functions
            initFuncs = []
            updateFuncs = []
            for fun in funcs:
                try:
                    initFuncs.append(getattr(fun.__self__, "init_" + fun.__name__))
                    updateFuncs.append(getattr(fun.__self__, "update_" + fun.__name__))
                except AttributeError:
                    # determine module
                    module = __import__(fun.__module__)
                    initFuncs.append(getattr(module, "init_" + fun.__name__))
                    updateFuncs.append(getattr(module, "update_" + fun.__name__))
            # call the init functions and store the relevant interpolation stacks
            t = interpolate(t0, tf, LINEAR)
            t.pop(0)
            stacks = []
            for fun, vars in zip(initFuncs, args):
                vars.insert(0, rate)
                vars.insert(0, tf)
                vars.insert(0, t0)
                temp = fun(*vars)
                vars.pop(0)
                vars.pop(0)
                vars.pop(0)
                stacks.append(temp)
            # now call the update functions for all time points in t and render each frame
            with self.video() as r:
                for _ in t:
                    for fun, vars, stack in zip(updateFuncs, args, stacks):
                        if stack:
                            val = stack.pop()
                            vars.insert(0, val)
                            fun(*vars)
                            vars.pop(0)
                    r()

    def multiplay(
        self,
        objArray,
        func,
        args=None,
        t0=0,
        tf=2,
        rate=EASE_IN_OUT,
        render=None,
        testRender=False,
    ):
        """
        A more powerful version of play - allows one to specify a singular function
        to be applied to a list of objects. Example:
        multiplay([ball, block, vector], "shift", [[0, 5]]) will shift ball, block,
        and vector by 5 in the y-direction.

        Args:
            objArray (list): List of objects to apply function to.
            func (str): Function wrapped in quotes. Example: "rotate" will call
                ball.rotate, block.rotate, etc.
            args (list[list], optional): List of lists in which each list maps to an
                object in objArray. If args is not as long as objArray, then the last
                list will be applied to the remaining objects. Defaults to None.
            t0 (int, optional): Only needed for backwards compatibility. You would
                never really need to change this. Defaults to 0.
            tf (int, optional): If t0 is 0, tf is the amount of time the animation
                runs for in seconds. Defaults to 2.
            rate (tuple, optional): Bezier-determined rate to use. Defaults to
                EASE_IN_OUT.
            render (bool, optional): Determines whether or not to render out the video.
                Defaults to None.
            testRender (bool, optional): Allows one to see the final state of an
                animation in the UI exactly as it would be rendered in a movie. Slows
                things down, but very useful when debugging... Defaults to False.

        Raises:
            CustomError: requires func to be string and args to be list
            CustomError: general error in which function could not be retrieved
                from object definition.
            CustomError: general error in which function could not be retrieved
                from object definition.
        """
        if render == None:
            render = self.render
        # adjust for args not being passed in - use empty arguments for each function
        if args == None:
            args = []
        # first, check to make sure func and args are lists
        if type(func) is list or type(args) is not list:
            raise CustomError(
                "func must be string and args must be list in order to be passed into multiplay()"
            )
        objArray = flatten(objArray)
        if args == []:
            args.append([])
        while len(args) < len(objArray):
            args.append(args[-1])
        # just call the raw function if not rendering (doesn't work with lambdas though!)
        # if using lambdas, pass in "testRender=True"
        if not render and not testRender:
            funcs = []
            for obj in objArray:
                try:
                    funcs.append(getattr(obj, func))
                except:
                    raise CustomError("could not get function from obj")
            for fun, vars in zip(funcs, args):
                fun(*vars)
            # fix for f.num
            if render != False:
                self.num += (tf - t0) * FRAME_RATE
        else:
            # determine the init and update functions
            initFuncs = []
            updateFuncs = []
            for obj in objArray:
                try:
                    initFuncs.append(getattr(obj, "init_" + func))
                    updateFuncs.append(getattr(obj, "update_" + func))
                except:
                    raise CustomError("could not get function from obj")
            # call the init functions and store the relevant interpolation stacks
            t = interpolate(t0, tf, LINEAR)
            t.pop(0)
            stacks = []
            for fun, vars in zip(initFuncs, args):
                vars.insert(0, rate)
                vars.insert(0, tf)
                vars.insert(0, t0)
                temp = fun(*vars)
                vars.pop(0)
                vars.pop(0)
                vars.pop(0)
                stacks.append(temp)
            # now call the update functions for all time points in t and render each frame
            with self.video() as r:
                for _ in t:
                    for fun, vars, stack in zip(updateFuncs, args, stacks):
                        if stack:
                            val = stack.pop()
                            vars.insert(0, val)
                            fun(*vars)
                            vars.pop(0)
                    r()

    def superplay(
        self,
        objArray,
        funcArray,
        args=None,
        t0=0,
        tf=2,
        rateArray=EASE_IN_OUT,
        render=None,
        testRender=False,
    ):
        """
        A more powerful version of play() and multiplay(), but necessarily more complex.
        Example:
        superplay([balls, blocks], ["shift", "rotate"],\
            [*len(balls)*[[7]], [Y, 2*PI]], rateArray=[*len(balls)*[[EASE]], LINEAR])
        will shift balls by 7 in the x-direction with a rate of EASE and rotate the
        blocks about the Y axis by an angle of 2*PI with a LINEAR rate at the same time.

        Args:
            objArray (list): List of objects.
            funcArray (list[str]): List of functions (wrapped in quotes) to apply to
                each object in objArray.
            args (list[list], optional): List of lists of arguments to be passed into
                the respective function calls. If args is shorter than funcArray or
                objArray, the last list of args will be applied to the remaining
                objects/functions. Defaults to None.
            t0 (int, optional): Same as play()/multiplay(). Defaults to 0.
            tf (int, optional): Same as play()/multiplay(). Defaults to 2.
            rateArray (list, optional): List of rates to be applied to each function.
                Defaults to EASE_IN_OUT
            render (bool, optional): Same as play()/multiplay(). Defaults to None.
            testRender (bool, optional): Same as play()/multiplay(). Defaults to False.

        Raises:
            CustomError: requires args to be a list.
            CustomError: general error - could not retrieve function for object.
            CustomError: general error - could not retrieve function for object.
        """
        if render == None:
            render = self.render
        # adjust for args not being passed in - use empty arguments for each function
        if args == None:
            args = []
        # fix for funcArray / rateArray not being list
        if type(funcArray) is not list:
            funcArray = [funcArray]
        if type(rateArray) is not list:
            rateArray = [rateArray]
        # check to make sure args is list
        if type(args) is not list:
            raise CustomError(
                "args must be list in order to be passed into superplay()"
            )
        objArray = flatten(objArray)
        if args == []:
            args.append([])
        # fix length of funcArray, args, and rateArray to be the same as length of objArray
        while len(funcArray) < len(objArray):
            funcArray.append(funcArray[-1])
        while len(args) < len(objArray):
            args.append(args[-1])
        while len(rateArray) < len(objArray):
            rateArray.append(rateArray[-1])
        # just call the raw function if not rendering (doesn't work with lambdas though!)
        # if using lambdas, pass in "testRender=True"
        if not (render or testRender):
            funcs = []
            for obj, func in zip(objArray, funcArray):
                try:
                    funcs.append(getattr(obj, func))
                except:
                    raise CustomError("could not get function from obj")
            for fun, vars in zip(funcs, args):
                fun(*vars)
            # fix for f.num
            if render != False:
                self.num += (tf - t0) * FRAME_RATE
        else:
            # determine the init and update functions
            initFuncs = []
            updateFuncs = []
            for obj, func in zip(objArray, funcArray):
                try:
                    initFuncs.append(getattr(obj, "init_" + func))
                    updateFuncs.append(getattr(obj, "update_" + func))
                except:
                    raise CustomError("could not get function from obj")
            # call the init functions and store the relevant interpolation stacks
            t = interpolate(t0, tf, LINEAR)
            t.pop(0)
            stacks = []
            for fun, vars, rate in zip(initFuncs, args, rateArray):
                vars.insert(0, rate)
                vars.insert(0, tf)
                vars.insert(0, t0)
                temp = fun(*vars)
                vars.pop(0)
                vars.pop(0)
                vars.pop(0)
                stacks.append(temp)
            # now call the update functions for all time points in t and render each frame
            with self.video() as r:
                for _ in t:
                    for fun, vars, stack in zip(updateFuncs, args, stacks):
                        if stack:
                            val = stack.pop()
                            vars.insert(0, val)
                            fun(*vars)
                            vars.pop(0)
                    r()

def resetAll():
    """Resets the entire UI.

    Returns:
        Camera: the resulting Camera object. Not really needed that often.
    """
    # delete all data except worlds
    for bpy_data_iter in (
        D.objects,
        D.meshes,
        D.cameras,
        D.curves,
        D.materials,
        D.particles,
    ):
        for id_data in bpy_data_iter:
            bpy_data_iter.remove(id_data)
    # unlink collections
    scene = C.scene
    for c in scene.collection.children:
        scene.collection.children.unlink(c)
    # delete collections
    for c in D.collections:
        if not c.users:
            D.collections.remove(c)
    # reset 3D cursor location
    scene.cursor.location = ORIGIN
    scene.cursor.rotation_mode = "QUATERNION"
    scene.cursor.rotation_quaternion = mut.Quaternion((1, 0, 0, 0))
    # make background black
    scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = BLACK
    # change viewport to rendered mode
    for area in C.screen.areas:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = "RENDERED"
    # turn off bloom
    if ev.use_bloom:
        toggleGlow()
    # instantiate camera
    return Camera()

def script_init(folderName, render=True):
    """Initializes any script.

    Args:
        folderName (str): name of folder to place output videos into.
        render (bool, optional): whether or not to render the animations in the
            script. Defaults to True.

    Returns:
        tuple: (the starting time, the Frame object for the script, and the Camera)
    """
    # error checking
    if folderName == None:
        raise CustomError("folderName must be passed into script_init()")
    print("\n\nBEGIN")
    cam = resetAll()
    start_time = time.time()
    # poor man's check for __file__:
    if folderName[0] == "\\":
        # "\filename.py" -> only want "filename"
        folderName = folderName[1 : len(folderName) - 3]
    elif folderName[0] == "C":
        # C:\...\main\filename.py" -> only want "filename"
        folderName = os.path.basename(folderName)
        folderName = folderName[0 : len(folderName) - 3]
    f = Frame(0, folderName, render)
    f.file = folderName + "_"
    return (start_time, f, cam)

def script_terminate(startTime, f=None):
    """Terminates a script.

    Args:
        startTime (float): the starting time of the script.
        f (Frame, optional): the Frame object associated with the script. Defaults
            to None.

    Raises:
        CustomError: startTime must be passed in.
    """
    # error checking
    if startTime == None:
        raise CustomError("startTime must be passed into script_terminate()")
    # set to camera view
    for area in C.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces[0].region_3d.view_perspective = "CAMERA"
            break
    # print some useful stuff
    if f != None:
        print("f.num at end of each method:")
        for num in f.sceneEnds:
            print("\t" + str(num))
    timeFormatter(time.time() - startTime, True)
    timeFormatter(time.time(), False)
    print("END\n")

def end_scene(frame, variables, stack, reset=None):
    """Called at the end of any scene.

    Args:
        frame (Frame): Frame object for that scene.
        variables (list): list of remaining defined variables in that scene.
        stack (list): the call-stack associated with the scene.
        reset (bool, optional): whether or not to reset the UI. Defaults to None.

    Raises:
        CustomError: frame, variables, and stack must be passed in

    Returns:
        Camera/None: Camera if resetting, otherwise none.
    """
    # error checking
    if frame == None or variables == None or stack == None:
        raise CustomError("frame, variables, and stack must be passed into end_scene()")
    if reset == None:
        reset = frame.render
    print("stack variables:")
    for var in variables:
        print("\t" + var)
    print(stack[0][3] + "() ended")
    print(f"current f.num: {frame.num}")
    # set to camera view
    for area in C.screen.areas:
        if area.type == "VIEW_3D":
            area.spaces[0].region_3d.view_perspective = "CAMERA"
            break
    # append f.num to object
    frame.sceneEnds.append(frame.num)
    if reset:
        return resetAll()
    else:
        return None
