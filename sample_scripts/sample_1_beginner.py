import importlib
import peeps
importlib.reload(peeps)
from peeps import *  # pylint: disable=unused-wildcard-import
(start_time, f, cam) = script_init(__file__, False)

# a block moving around with a lamp in the midst
def block_with_lamp():
    # let's go as simple as we can, by starting with a red block
    block = Block(6, 6, 6, ORIGIN, RED)
    # just looks like a square - we can tell it's a block for sure once we rotate it.
    # we'll rotate it about the y-axis first by 45 degrees.
    block.rotate(Y, PI/4)
    # looks a bit weird... - how about we now rotate it about the x-axis?
    block.rotate(X, PI/6)
    # looks a bit more like a block, but we're still missing some perspective.
    # we can use a Lamp to help out.
    Lamp((-1, 1, 7))
    # nice, looks pretty clean! let's shift the block to the right and darken it...
    block.fadeShift(BLACK, 7)
    # ... so we can animate it into its previous position using f.play(). we'll make this
    # a 4-second animation
    f.play([block.fadeShift], [[RED, -7]], tf=4)
    # let's animate a swift rotation of the block.
    f.play([block.rotate], [[Z, 6*PI]], tf=4)
    # we can even make the block transparent! let's put a green Ball inside the block
    ball = Ball(2)
    ball.color(GREEN)
    # just to prove it's there, we'll move the block out of the way for a sec.
    f.play([block.shift], [[0, 7]])
    f.play([block.shift], [[0, -7]])
    # now let's make the block transparent - we should be able to see the green ball.
    f.play([block.transparent], [[0.1]])
    # that's enough for this one - to delete everything and reset the scene, change the
    # end_scene() call below to accept True as its last argument.
    return end_scene(f, dir(), inspect.stack(), False)

# graphing a simple function
def graphing_function():
    # for this one, we can use GraphFlexible, probably the most flexible (hence the name)
    # way of graphing a 2D function
    graph = GraphFlexible("x", "f(x)")
    # even before we can see anything, I can already tell the labels are a bit too far
    # away from the graph and awkwardly placed. we could have used the xLabelShift and
    # yLabelShift parameters in the constructor we just called, but let's say we didn't
    # know that. how do we reposition them? first, let's find out what the labels are
    # called by pretty-printing the graph (a super useful skill that's easy to do).
    prettyPrint(graph)
    # immediately, we can see in the console all the properties of the Python object
    # graph. it looks like xLabel and yLabel are what we're looking for. let's shift
    # them without animating anything yet.
    graph.xLabel.shift(-2, 1)
    graph.yLabel.shift(2, 2)
    # much better! now, let's animate the graph fading in.
    f.play([graph.fade], [[WHITE]])
    # now, let's draw out a function. i like cosines, so why don't we try one of those?
    # we need a simple lambda function to define our cosine wave. lambdas are sort of an
    # advanced Python topic, but all we're doing here is defining a function that accepts
    # an argument t and returns the cosine of that argument. try it out by printing
    # cosine(PI) or cosine(0).
    cosine = lambda x: np.cos(x)
    # now that we have our cosine function, let's draw it.
    graph.draw(f, cosine)
    # yes, it really was that simple! our cosine function is looking a little wimpy down
    # there, so let's make it a bit more prominent on our screen. first, let's delete
    # the old curve - we can figure out from prettyPrint() that graph.curve is what we're
    # after.
    graph.curve.delete()
    # so let's define a more prominent cosine function and draw it out
    bolderCosine = lambda x: 5*np.cos(x) + 7
    graph.draw(f, bolderCosine)
    # neat! let's try one last function: a simple exponential. we can pass in our lambda
    # function directly into the graph.draw() function without defining it beforehand.
    # also, we can adjust xTruncate and yTruncate so our graph takes up more space.
    graph.curve.delete()
    graph.draw(
        f, lambda x: np.exp(x/9), runtime=5, xTruncate=0, yTruncate=0, curveColor=GREEN
    )
    # that completes this one - let's fadeShift everything downwards and call it a day.
    f.multiplay([graph, graph.curve], "fadeShift", [[BLACK, 0, -5]])
    # remember to change the end_scene() call argument to True to clean up the scene.
    return end_scene(f, dir(), inspect.stack(), False)

# simple latex derivation - requires knowledge of latex
def latex_derivation():
    # start with a function - let's title sequence it in
    startingTex = Tex("f(t)=3\\sin{(t)}+t^2", 0.7, False, (0, 10, 0), True, f)
    # what's the derivative of the function with respect to time?
    derivativeTex = Tex(
        "\\frac{d}{dt}f(t)=\\frac{d}{dt}\\left[3\\sin{(t)}+t^2\\right]",\
        0.7, False, (1.3, 5, 0))
    # the previous Tex is dark - we haven't colored it yet, because we want to morph
    # it in from the previous Tex - let's do it
    derivativeTex.morphFrom(f, startingTex)
    # simplify and morph that in from the previous Tex
    simplifyTex1 = Tex(
        "\\frac{d}{dt}f(t)=3\\frac{d}{dt}\\left[\\sin{(t)}\\right]+\\frac{d}{dt}\\left[t^2\\right]",\
        0.7, False, (3.4, -1, 0))
    simplifyTex1.morphFrom(f, derivativeTex)
    # top it off with the answer
    simplifyTex2 = Tex(
        "\\frac{d}{dt}f(t)=3\\cos{(t)}+2t",\
        0.7, False, (-1, -7, 0))
    simplifyTex2.morphFrom(f, simplifyTex1)
    # let's fade everything out and shift it into the screen at the same time.
    # we're going to want to use f.multiplay for this - the same function applied to
    # multiple objects at the same time
    f.multiplay(
        [startingTex, derivativeTex, simplifyTex1, simplifyTex2],
        "fadeShift",
        [[BLACK, 0, 0, -5]]
    )
    # we don't want those dark objects to continue cluttering the screen.
    # once we're done with them, we can delete them manually or just change the
    # end_scene() call to have True passed in as the last argument.
    delete([startingTex, derivativeTex, simplifyTex1, simplifyTex2])
    return end_scene(f, dir(), inspect.stack(), False)

# we can do everything in the previous function with more ease by using the TexManager
def introduction_to_TexManager():
    # initialize TexManager with initial Tex
    t = TexManager(f, "f(t)=3\\sin{(t)}+t^2", (0, 10, 0), 0.7, False)
    # add a new Tex in and morph it from the previous.
    # note that we have to pass in relative=False to specify that the origin is absolute,
    # not relative to the previous Tex
    t.insert("\\frac{d}{dt}f(t)=\\frac{d}{dt}\\left[3\\sin{(t)}+t^2\\right]",
        (1.3, 5, 0), relative=False)
    # let's keep going
    t.insert(
        "\\frac{d}{dt}f(t)=3\\frac{d}{dt}\\left[\\sin{(t)}\\right]+\\frac{d}{dt}\\left[t^2\\right]",
        (3.4, -1, 0), relative=False)
    t.insert(
        "\\frac{d}{dt}f(t)=3\\cos{(t)}+2t",
        (-1, -7, 0), relative=False)
    # and that's all it took! we now have exactly the same scene from the previous
    # function with half the amount of code. if you ever need to access individual Tex
    # objects, they're found at t.texs. if you need to see what Tex objects are currently
    # a part of the TexManager, you can call t.print().
    t.print()
    # TexManager also comes with its own built-in fadeShift() function and we can delete
    # the objects right after the fadeShift() as well.
    t.fadeShift(True, [BLACK, 0, 0, -5], True)
    return end_scene(f, dir(), inspect.stack(), False)

# draw out the electric field lines for two point charges
def creating_field_lines():
    # we'll start by creating two particles of opposite charge and the same mass
    posCharge = PointCharge(1, (10, 10, 0), "+", ELEM_CHARGE, MASS_PROTON)
    negCharge = PointCharge(1, (-10, -10, 0), "-", -ELEM_CHARGE, MASS_PROTON)
    # let's animate them fadeShifting towards each other. note how we want each call
    # to fadeShift() to accept different arguments for each object.
    f.multiplay([posCharge, negCharge], "fadeShift", [[A1, -5, -5], [A5, 5, 5]])
    # now let's generate the field lines between the two charges. let's do 8 lines
    # per charge.
    (fieldLines, _, _) = generateFieldLines(
        [posCharge, negCharge], numFactor=8
    )
    # can't see them... let's give them a yellowish color.
    for line in fieldLines:
        line.color(A3)
    # not bad, but is there any way we can animate this though? yes, there is and it's
    # just as easy! let's start by deleting the field lines.
    delete(fieldLines)
    # now, let's call playFieldLines(). just so you don't have to stare at your screen
    # for five minutes, we'll set dLength to be a large value of 0.5 and use the same
    # settings we used for generateFieldLines().
    playFieldLines(f, dLength=0.5, chargeList=[posCharge, negCharge], numFactor=8)
    # and that just about does it! remember to set the final argument in the end_scene()
    # call below to True to reset the scene.
    return end_scene(f, dir(), inspect.stack(), False)

block_with_lamp()
# graphing_function()
# latex_derivation()
# introduction_to_TexManager()
# creating_field_lines()

script_terminate(start_time)