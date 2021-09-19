import importlib
import peeps
importlib.reload(peeps)
from peeps import *  # pylint: disable=unused-wildcard-import
(start_time, f, cam) = script_init(__file__, False)

# shifting a ball along a weird path at constant speed
def ball_shift_by_path():
    # let's start by creating a path for a ball to follow
    relativePathNodes = [
        (4, 4, 0),
        (1, 1, 0),
        (-5, 5, 0),
        (-5, -5, 0),
        (10, -10, 0),
        (-5, -5, 0),
        (-5, 5, 0),
        (1, 1, 0)
    ]
    path = RelativeNodeWires(relativePathNodes, 0.2)
    path.shift(0, 0, -5)
    f.play([path.fadeShift], [[OCEAN, 0, 0, 5]])
    # position a ball at the beginning of the path
    ball = Ball(0.7, addition(relativePathNodes[0], (-1, -1, 0)))
    f.play([ball.fadeShift], [[RED, 1, 1]])
    # suppose we want to shift the ball at constant speed to the other end of the path,
    # but we want the animation to be a length of ~10 seconds. how do we accomplish this
    # without just trying different speeds and iterating like crazy? let's start by
    # figuring out the total length of the path. we can just add up the magnitudes
    # of all the relativePathNodes, excluding the first one:
    totalLength = 0
    for node in relativePathNodes[1:]:
        totalLength += mag(node)
    # now that we have the length, dividing it by the animation runtime (10 s) will give
    # us the desired speed of the ball along the path (in units per second)
    speed = totalLength/10
    # dividing this speed by the frame rate will give us the magnitude of the ball's
    # shift per frame.
    frameShift = speed/FRAME_RATE
    # now all we have to do, in principle, is shift the ball by a magnitude of
    # frameShift on each frame. it's not so easy, however, because we have to worry
    # about directions and undershooting corners. the most robust way to do this will
    # probably be with f.video() - it might be possible to do it with the standard
    # f.play(), but the it'll be difficult to keep the speed of the ball precisely
    # constant.
    curr = ball.origin
    with f.video() as r:
        for shift in relativePathNodes[1:]:
            # imagine we hit a corner previously. we'll use curr to determine how much
            # the ball has undershot the current node.
            diff = subtraction(ball.origin, curr)
            # shift the ball to the node and then prepare to shift along the new path
            # by an amount of frameShift - mag(diff)
            ball.shift(*negate(diff))
            # figure out the correct direction to travel in
            direction = mut.Vector(shift).normalized()
            # travel the remaining distance in a frameShift
            ball.shift(*((frameShift - mag(diff))*direction))
            # render this frame and prepare to move along the next path
            r()
            # what is the total length of the next shift?
            lenShift = mag(shift) - (frameShift - mag(diff))
            # how many steps should we take in this direction? always undershoot with
            # np.floor() instead of np.ceil().
            numSteps = int(np.floor(lenShift/frameShift))
            for _ in range(numSteps):
                ball.shift(*(frameShift*direction))
                r()
            # finally, update curr for the next iteration
            curr = addition(shift, curr)
        # if there's any remaining amount due to roundoff, shift the rest and render
        diff = subtraction(ball.origin, curr)
        ball.shift(*negate(diff))
        r()
    return end_scene(f, dir(), inspect.stack(), False)

# moving multiple balls in an elliptical path
def elliptical_shifts():
    # let's define a thin elliptical path in the viewport
    xAxis = 19
    yAxis = 9
    path = Ellipse(xAxis, yAxis, thickness=0.02, resolution=3000)
    path.shift(0, 0, -5)
    f.play([path.fadeShift], [[WHITE, 0, 0, 5]])
    # what if we wanted to shift some balls along the path - how would we do it? you
    # could just use f.video() and make tiny adjustments on every single frame, but
    # i thought this would be a good opportunity to introduce shifting with lambda
    # functions. let's define a parametric representation of an ellipse in 2D (note
    # that we'll need z too if we want to use lambdas). we'll start by choosing a
    # rotational speed, omega.
    omega = 1
    # we need this value of omega to immediately be instantiated in the lambda functions,
    # so that all of them are really just functions of t
    x = lambda t, omega=omega: xAxis*np.cos(omega*t)
    y = lambda t, omega=omega: yAxis*np.sin(omega*t)
    z = lambda t, omega=omega: 0
    # now that we have our lambdas, we can instantiate three balls that are split along
    # equal angles of the ellipse
    angles = interpolate(0, 2*PI, LINEAR, 3)
    # with three intervals, we've double-counted 0 and 2*PI
    angles.pop(-1)
    # prepare for list comprehension overload...
    tVals = [ang/omega for ang in angles]
    positions = [(x(t), y(t), z(t)) for t in tVals]
    colors = [RED, GREEN, BLUE]
    fadeShifts = [[col, *pos] for col, pos in zip(colors, positions)]
    balls = [Ball(1) for _ in range(3)]
    f.multiplay(balls, "fadeShift", fadeShifts)
    # now that we have our balls, we can't just shift them all with the same lambda
    # functions, because then, they'll all just be stacked on top of each other. we need
    # to use phase shifts (ang) to split up appropriate lambda functions for each ball.
    lambs = [
        (
            lambda t, omega=omega, phi=phi: xAxis*np.cos(omega*t + phi),
            lambda t, omega=omega, phi=phi: yAxis*np.sin(omega*t + phi),
            lambda t, omega=omega, phi=phi: 0,
        ) for phi in angles
    ]
    # get the arguments in the right format for f.multiplay()
    shiftArgs = [[0, 0, 0, *lamb] for lamb in lambs]
    # note that when shifting with lambda functions, you'll have to use testRender=True
    # if you're interested in the viewport preview, otherwise, when previewing
    # animations, shift() will take the "0, 0, 0" literally
    f.multiplay(balls, "shift", shiftArgs, tf=2*PI/omega, rate=LINEAR, testRender=True)
    # it looks like nothing happened, because we just took each of the balls full circle!
    # if you try changing tf, you can see multiplay() moving the balls around the
    # elliptical path. what we've shown in this scene is that if you can define
    # a parametric representation for a path as a function of time (x(t), y(t), z(t)),
    # you can shift anything along that path!
    return end_scene(f, dir(), inspect.stack(), False)

# a weird sinusoidal circle shift
def sinusoidal_circle():
    # start with a thin circular path
    dist = 10
    path = Ring(dist, 0.02, (0, 0, -5))
    f.play([path.fadeShift], [[WHITE, 0, 0, 5]])
    # a humble ball sits at the bottom
    ball = Ball(1)
    f.play([ball.fadeShift], [[CHOCOLATE, 0, -dist]])
    # we want to swing the ball back and forth about the ring. we can do this with
    # cosine_interpolate() and some lambdas.
    angs = cosine_interpolate(PI)
    # by calling print(angs), we can see that angs oscillates from PI to -PI and then
    # back around to PI. this suggests that we should have the 0 angle at the top with
    # PI and -PI extending back and forth around the circle. to be consistent with the
    # x-y coordinate system, we'll use a phase shift of PI/2.
    x = lambda theta: dist*np.cos(theta + PI/2)
    y = lambda theta: dist*np.sin(theta + PI/2)
    # now, all we have to do is change the ball's position to (x(ang), y(ang), 0) for
    # each ang in angs and render out each frame
    with f.video() as r:
        for ang in angs:
            ball.shift(*subtraction((x(ang), y(ang), 0), ball.origin))
            r()
    return end_scene(f, dir(), inspect.stack(), False)

# cross product evaluations in 3D
def cross_product_demo():
    # let's move to three dimensions with a GraphSpace
    graph = GraphSpace(ticksOn=False, labelsOn=False, gridOn=True)
    f.play([graph.color])
    # we'll move to a clearer view and rotate the y-label at the same time
    f.play(
        [camQuatTransform, graph.y.rotateLabels],
        [[(23.638, 22.556, 25.640), (0.3555, 0.1849, 0.4227, 0.8129)], [X, -PI/2]]
    )
    # create two vectors, A and B, along the x and y axes, respectively
    A = Vector(1, 0, 0, (15, 0, 0), A1)
    B = Vector(0, 1, 0, (0, 15, 0), A4)
    f.multiplay([A, B], "shift", [[-15], [0, -15]])
    # compute the cross product of these two vectors (hint: it should point along the
    # z-axis and have a magnitude of 1)
    CNormal = mut.Vector(A.normal).cross(mut.Vector(B.normal))
    C = Vector(*CNormal, (0, 0, 15), A7)
    f.play([C.shift], [[0, 0, -15]])
    # create a legend in the top right corner. start with the colors.
    blocks = [
        Block(1, 1, 1, (-13, 0, z)) for z in np.arange(0, 7, 2.5)
    ]
    for block, col in zip(blocks, [A1, A4, A7]):
        f.play([block.color], [[col]], tf=0.5)
    # working with Texs in 3D requires some finagling...
    expressions = [
        "\\overrightarrow{\\textbf{A}}",
        "\\overrightarrow{\\textbf{B}}",
        "\\overrightarrow{\\textbf{A}}\\times\\overrightarrow{\\textbf{B}}",
    ]
    # finagle shifts until they're desirable
    shifts = [
        (-1.3, 1.3, 0),
        (-1.3, 1.3, 0.3),
        (-2.5, 2.5, 0.5)
    ]
    texs = [
        Tex(expression, 0.5, origin=addition(block.origin, shift))\
            for expression, block, shift in zip(expressions, blocks, shifts)
    ]
    for t in texs:
        t.cameraTrack()
    f.multiplay(texs, "titleIn")
    # now that our legend's in place, we can start to have some fun! let's transform
    # A and B while displaying the cross product the entire way.
    ATransform = (1, 5, 0)
    BTransform = (-1, 0, 2)
    # first, figure out how A and B are going to transform by calling init_transform()
    # on each. this will return the stack used to transform each vector.
    AStack = A.init_transform(0, 4, EASE_IN_OUT, *ATransform)
    BStack = B.init_transform(0, 4, EASE_IN_OUT, *BTransform)
    # now, let's perform the transformations at the same time while updating C the
    # entire way
    with f.video() as r:
        # both stacks should go to zero at the same time, but this is just a fail-safe
        while len(AStack) > 0 and len(BStack) > 0:
            A.transform(*AStack.pop())
            B.transform(*BStack.pop())
            # compute the cross product of A and B
            CNormal = mut.Vector(A.normal).cross(mut.Vector(B.normal))
            # then, update C
            C.transform(*CNormal)
            r()
    # not bad! things are taking a lot longer now, because vector transform() calls
    # delete the previous vector and replace it with a new one - we're now doing this
    # on every single frame. let's finish things off by rotating A about the axis of C
    # and noting how the cross product changes. let's start by normalizing C to get
    # our rotation axis.
    rotationAxis = tuple(mut.Vector(C.normal).normalized())
    rotationStack = A.init_rotate(0, 4, EASE_IN_OUT, rotationAxis, 2*PI)
    # we'll finish this one up similarly to how we did the transforms
    with f.video() as r:
        while len(rotationStack) > 0:
            # note that the rotation stack only holds the angle to rotate through, not
            # the axis
            A.rotate(rotationAxis, rotationStack.pop())
            # compute the cross product of A and B
            CNormal = mut.Vector(A.normal).cross(mut.Vector(B.normal))
            # then, update C
            C.transform(*CNormal)
            r()
    # looks like nothing happened, because we rotated A in a full circle about C - you'll
    # want to render this one out to see the full picture
    return end_scene(f, dir(), inspect.stack(), False)

ball_shift_by_path()
# elliptical_shifts()
# sinusoidal_circle()
# cross_product_demo()

script_terminate(start_time)