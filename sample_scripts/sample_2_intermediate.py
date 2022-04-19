import importlib
import peeps

importlib.reload(peeps)
from peeps import *

(start_time, f, cam) = script_init(__file__, False)

# manipulating vectors to do weird things
def manipulating_vectors():
    # let's create some vectors stretching out in many angles. first, we need to figure
    # out what those angles are via interpolation.
    angs = interpolate(0, 2 * PI, LINEAR, 8)
    # by having 8 intervals between 0 and 2*PI inclusive, we've double counted the 0
    # angle. let's fix that.
    angs.pop(-1)
    # now, let's make a short animation where we pop out a vector along each of these
    # angles at 10-frame intervals or 1/6 of a second. we do this using the f.video()
    # context-manager, the most powerful way to make an animation, since it gives you
    # control over what happens on every single frame. first, let's initialize the
    # vectors.
    vecs = []
    # within the video context-manager, any time we call r(), that renders a frame for
    # the animation. once we exit the context-manager, all the frames are concatenated
    # into a video.
    with f.video() as r:
        # for each of the angles...
        for ang in angs:
            # ...create a vector pointing in the direction of the angle and with a
            # magnitude of 5
            vecs.append(Vector(5 * np.cos(ang), 5 * np.sin(ang), 0, ORIGIN, OCEAN))
            # wait for 10 frames
            for _ in range(10):
                r()
    # i'm now interested in shifting the vectors radially away from the origin. how
    # might i do that? we can record the necessary shift for each vector and then apply
    # f.multiplay() to map each corresponding vector with its shift
    shifts = []
    for ang in angs:
        # we'll shift a distance of 7 away from the origin
        shifts.append([7 * np.cos(ang), 7 * np.sin(ang), 0])
    # now call multiplay()
    f.multiplay(vecs, "shift", shifts)
    # note that the origin of each vector is the orange dot at the tail of the vector.
    # you can see the origin of any object in Blender by clicking on it and looking for
    # the orange dot. rotating any object rotates it about its origin. for instance,
    # let's rotate each vector about its origin by an angle of 90 degrees.
    f.multiplay(vecs, "rotate", [[Z, PI / 2]])
    # since each vector has a different origin, each one rotated about its respective
    # tail by PI/2 radians. we can actually change the origins of all the vectors too
    # by calling changeOriginTo(). first, we should probably record the current origins
    # though.
    originalOrigins = []
    for vec in vecs:
        originalOrigins.append(vec.origin)
    # if we now want to spin these vectors around in a spiral, we should place each
    # vector's origin at the world origin before rotating them.
    for vec in vecs:
        vec.changeOriginTo(*ORIGIN)
    # now, if we select any object in the UI, we see that its origin is at the world
    # origin. calling rotate on any of these vectors now will spin it about the world
    # origin, not its tail. let's do it! you won't be able to see it in the UI, because
    # we're making a full circle, but you'll be able to see this behavior once you render
    # out the videos for this script. also, after calling changeOriginTo() on a Vector,
    # you should call superRotate() instead of rotate(), since Vector.superRotate() calls
    # the Blobject implementation of rotate(), while Vector.rotate() calls the Vector
    # implementation, which is really just a transform() call (we'll get to that in a
    # sec).
    f.multiplay(vecs, "superRotate", [[Z, 2 * PI]])
    # now, let's restore the original origins of the vectors. in case you've never seen
    # it before, we can use zip() to iterate through two iterables concurrently.
    for vec, og in zip(vecs, originalOrigins):
        vec.changeOriginTo(*og)
    # now, let's do something really weird. let's transform each vector so that it points
    # along the x-axis and has a magnitude of 10 while also shifting each vector to the
    # world origin at the same time. how do we do this? we need to figure out the shift
    # for each vector, but luckily, since we haven't manipulated the vectors too much,
    # each shift is just the negative of the original shift we applied to it.
    for i in range(len(shifts)):
        shifts[i] = negate(shifts[i])
    # we'll use this as an opportunity to introduce f.superplay(). while it's not as
    # powerful as the f.video() context-manager, it's probably the most complicated.
    # let's explain it via an example. we need to know our objects first. since we want
    # to shift() and transform() each vector at the same time, let's have two sets of
    # vectors as part of our objects, one set for shifting and the other for
    # transforming.
    objs = [*vecs, *vecs]
    # here, we're unpacking vecs twice into a larger list, so we just end up with one
    # long list of vecs repeated twice - no nested lists. what function are we calling
    # on each object in objs? let's call shift() on the first half of objs (all the
    # vectors) and transform() on the second half (again, all the vectors).
    funcs = [*len(vecs) * ["shift"], *len(vecs) * ["transform"]]
    # now, there's a lot going on there, but you can see that it works by calling
    # print(funcs). we start with ["shift"] and multiply it by len(vecs), which is 8 here
    # to get ["shift", "shift", "shift", "shift", "shift", "shift", "shift", "shift"].
    # then, we just unpack that into the larger list to avoid any nested lists. now we
    # just need the arguments for each function call in its own list:
    args = deepcopy(shifts)
    for _ in vecs:
        args.append([10])
    # those are all the puzzle pieces! we can even specify separate Bezier rates for each
    # function call, but that would seriously be overkill here - let's just call it.
    f.superplay(objs, funcs, args)
    # you can tell it stacked all the vectors on top of each other by moving each vector
    # out of the way to expose the ones underneath (simply select a vector and press 'G'
    # to move the vector around with your mouse). we're almost done here, let's just
    # fan out the vectors so that we end up with a similar situation to the one we
    # started out with. how much do we rotate each vector? by exactly the amounts
    # specified by angs:
    rotationArgs = []
    for ang in angs:
        rotationArgs.append([Z, ang])
    f.multiplay(vecs, "rotate", rotationArgs)
    # finally, let's pop the vectors out of the origin while fading them to black
    fadeShifts = []
    for ang in angs:
        fadeShifts.append([BLACK, 5 * np.cos(ang), 5 * np.sin(ang)])
    f.multiplay(vecs, "fadeShift", fadeShifts)
    delete(vecs)
    return end_scene(f, dir(), inspect.stack(), False)


# exploring graphs in 3D
def exploring_graphspace():
    # we'll begin this scene by instantiating a GraphSpace, which is a 3D graph
    graph = GraphSpace(ticksOn=False, labelsOn=False, gridOn=True)
    # let's use color() to fade the graph in
    f.play([graph.color])
    # by holding down your middle mouse button, you can navigate around the 3D viewport
    # in Blender and you'll notice that there is a z-axis that points out of the screen.
    # navigate around until you find a spot that shows all three axes clearly and then
    # use the keyboard shortcut Ctrl+Alt+0 where 0 is on your numpad. this will lock the
    # camera to the current view in your viewport. now, we'd like to know how the camera
    # is oriented and where it's located, so head up to the tab at the top of Blender
    # labeled "small" and then go over to the window labeled "Console" and type in the
    # following commands:
    # >>> C.scene.camera.location
    # >>> C.scene.camera.rotation_quaternion
    # copy the output of each and paste them in your script here without the Vector()
    # and Quaternion() outer bounds. alternatively, you can just use the ones that i
    # came up with:
    loc = (23.638, 22.556, 25.640)
    quat = (0.3555, 0.1849, 0.4227, 0.8129)
    # these specify the location and unique orientation of the camera after we've locked
    # it to our view. we can animate a transformation to this new state for the camera,
    # using f.play(). be sure to head back to the tab labeled "large" in Blender to run
    # your script.
    f.play([camQuatTransform], [[loc, quat]])
    # we now have a clean 3D view of our graph! let's rotate the y-label of the graph
    # so that it's more easily discernible. we can do this by calling rotateLabel()
    # on the y-axis of the graph. note that the labels don't rotate the way you'd expect
    # them to - this is a tricky bug in the library that i have yet to fix...
    f.play([graph.y.rotateLabels], [[X, -PI / 2]])
    # now, let's take it up a notch and demonstrate the circular magnetic field around a
    # straight current-carrying conductor. first, we need the wire, of course. it just
    # needs to be long enough to cover the whole screen.
    wire = Cylinder(0.2, 41, (0, -7, 0))
    # let's rotate it so it travels along the y-axis and color it brown
    wire.rotate(X, PI / 2)
    wire.color(BROWN)
    # let's shift it out and then we can animate it shifting in
    wire.shift(0, -42)
    f.play([wire.shift], [[0, 42]])
    # let's indicate to the viewer that the current is in the positive y-direction. we'll
    # use a Vector that points in the y-direction...
    currentDirection = Vector(0, 3, 0, (-1.5, 1, -1))
    # ...and animate it in.
    f.play([currentDirection.fadeShift], [[A7, 0, 0, 1]])
    # now, i want to label the current with an "I". positioning Tex's in three dimensions
    # is really tricky, but a decent heuristic to use is to just eyeball a spot to put
    # it and call cameraTrack() - from there, just iterate until you reach a position
    # you're happy with. note that you definitely want to set the 'twistable'
    # attribute in the constructor to True if you're working with Tex's in 3D.
    currentLabel = Tex("I", 0.6, True, (-2.5, 2, 1))
    currentLabel.cameraTrack()
    # let's title sequence it in
    f.play([currentLabel.titleIn])
    # we're now ready to generate the magnetic field vectors at specific intervals along
    # the y-axis to complete the scene. let's use intervals that are 10 units apart.
    # it'll be useful to go a bit out of bounds in the back for an animation that we're
    # going to perform in a sec. first, let's figure out where we want to put the
    # magnetic field vectors
    angs = interpolate(0, 2 * PI, LINEAR, 8)
    angs.pop(-1)
    fieldVecs = []
    with f.video() as r:
        for yVal in range(-40, 11, 10):
            for ang in angs:
                # compute the position of the relevant magnetic field vector
                position = (5 * np.sin(ang), yVal, 5 * np.cos(ang))
                # just point it radially away - we'll rotate it in a sec
                components = (np.sin(ang), 0, np.cos(ang))
                fieldVecs.append(Vector(*components, position, A3, 0.05, 0.3))
                # rotate the fieldVec by 90 degrees, so it points in the correct
                # direction per the right-hand-rule.
                fieldVecs[-1].rotate(Y, PI / 2)
                # render the current frame three times
                for _ in range(3):
                    r()
    # a little more cluttered than i thought it would be, but let's work with it. i
    # want a label to indicate the magnetic field, so let's take care of that.
    magneticLabel = Tex("\\overrightarrow{\\textbf{B}}", 0.5, True, (-4, -10, 6))
    magneticLabel.cameraTrack()
    f.play([magneticLabel.titleIn])
    # now for an elegant finishing touch. let's move these field vectors along the
    # length of the wire while twisting them around the wire. it'll take a bit of work,
    # but not as much as you might expect! we'll start by changing the origin of each
    # field vector to be its projection onto the y-axis:
    for vec in fieldVecs:
        vec.changeOriginTo(0, vec.origin[1], 0)
    # now that each field vector's origin lies on the y-axis, a simple superRotate()
    # will rotate the vectors about the axis itself! the entire animation is probably
    # best done through f.superplay().
    objs = [*fieldVecs, *fieldVecs]
    funcs = [*len(fieldVecs) * ["shift"], *len(fieldVecs) * ["superRotate"]]
    args = [*len(fieldVecs) * [[0, 10]], *len(fieldVecs) * [[Y, PI]]]
    # i want the call to f.superplay() to perform with a LINEAR rate, so that looping
    # the video indefinitely appears completely smooth...
    f.superplay(objs, funcs, args, tf=4, rateArray=LINEAR)
    # a super clean animation in three dimensions without all that much code!
    return end_scene(f, dir(), inspect.stack(), False)


# a simple circuit
def setting_up_a_circuit():
    # we're now going to set up a simple circuit with five elements. let's start with
    # a battery and fadeShift it in.
    battery = Battery(2, (0, -10, 0))
    f.play([battery.fadeShift], [[WHITE, 0, 3]])
    # let's throw a resistor into the mix. we'll keep everything at the same scale.
    resistor = Resistor(2)
    # let's rotate the resistor and fadeShift it to the right at the same time. we can
    # do this easily with f.play(). note how we pass in a separate set of arguments
    # to resistor.rotate and a separate set to resistor.fadeShift
    f.play([resistor.rotate, resistor.fadeShift], [[Z, PI / 2], [WHITE, 10]])
    # now how do we connect the two components together? we do so using NodeWires.
    # NodeWires simply draws out a curve between multiple nodes we specify via the grid
    # in the UI. NodeWires also smoothes out the corners between nodes.
    bottomRight = NodeWires([(5, -7, 0), (10, -7, 0), (10, -5, 0)], thickness=0.2)
    # let's shift it backwards and animate it fadeShifting in
    bottomRight.shift(0, 0, -5)
    f.play([bottomRight.fadeShift], [[WHITE, 0, 0, 5]])
    # we don't have a closed circuit yet, so let's keep going. why don't we throw in a
    # capacitor?
    capacitor = Capacitor(2)
    f.play([capacitor.fadeShift], [[WHITE, 0, 9]])
    # i realized over time that NodeWires can be a bit mentally taxing with having to
    # keep track of what feels like a million positions. much easier is using something
    # i designed as a result called RelativeNodeWires, one of my favorite Blobjects.
    topRight = RelativeNodeWires([(10, 5, 0), (0, 4, 0), (-5, 0, 0)], thickness=0.2)
    # the way it works is you only have to specify the absolute position of the first
    # node - every node after that is simply relative to the previous node. let's
    # animate this connection in.
    topRight.shift(0, 0, -5)
    f.play([topRight.fadeShift], [[WHITE, 0, 0, 5]])
    # we're gettin' there... let's add an ammeter now
    ammeter = Ammeter(2, (-10, 0, 0.2))
    # we'll fade it in as a gentle green, but first, we need some wiring. the way i like
    # to do this with ammeters/voltmeters is to just have wiring go straight through the
    # meter and lift the meter slightly above the wiring as a time-saving visual hack.
    leftWires = RelativeNodeWires(
        [(-5, 9, 0), (-5, 0, 0), (0, -16, 0), (5, 0, 0)], thickness=0.2
    )
    # let's shift the wiring/ammeter to the left without rendering
    f.multiplay([leftWires, ammeter], "shift", [[-10]], render=False)
    # now let's fadeShift them in as an animation
    f.multiplay(
        [leftWires, ammeter], "fadeShift", [[WHITE, 10], [brighter(GREEN, 10), 10]]
    )
    # we now have a closed circuit, but let's give it a voltmeter for a finishing touch.
    # we'll have the voltmeter measure the voltage across the capacitor.
    voltmeter = Voltmeter(2, (0, 0, 0.2))
    # gotta add some wiring too - let's have it stretch halfway and then we'll shift in
    # the rest of the way.
    voltmeterWires = RelativeNodeWires(
        [(5, 6, 0), (0, -6, 0), (-10, 0, 0), (0, 6, 0)], thickness=0.2
    )
    f.multiplay(
        [voltmeterWires, voltmeter],
        "fadeShift",
        [[WHITE, 0, 3], [brighter(GREEN, 10), 0, 3]],
    )
    # and that completes our circuit.
    return end_scene(f, dir(), inspect.stack(), False)


# simulating electrodynamics between charged particles
def electrodynamics():
    # we'll finish things off with a breather. let's start by creating a few charged
    # particles in random locations. gotta set the seed first.
    np.random.seed(5)
    charges = []
    for _ in range(4):
        # let's also randomize whether they're positive or negative
        isPositive = np.random.uniform() >= 0.5
        if isPositive:
            chargeStr = "+"
            theCharge = ELEM_CHARGE
        else:
            chargeStr = "-"
            theCharge = -ELEM_CHARGE
        charges.append(
            PointCharge(
                1,
                (20 * np.random.uniform(-1, 1), 10 * np.random.uniform(-1, 1), 0),
                chargeStr,
                theCharge,
            )
        )
        if isPositive:
            charges[-1].color(A1)
        else:
            charges[-1].color(A5)
    # now that the charges are in place, let's simulate some dynamics! it's as simple
    # as calling a function. you'll definitely have to wait for it to iterate through
    # each frame and compute velocities/accelerations though...
    simulateElectrodynamics(
        f, charges, initialMovement=3, showForces=False, tf=11, allowZMovement=False
    )
    return end_scene(f, dir(), inspect.stack(), False)


manipulating_vectors()
# exploring_graphspace()
# setting_up_a_circuit()
# electrodynamics()

script_terminate(start_time)
