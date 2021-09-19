from constants import CustomError, G_CONST, A2, dt
from blobjects.shapes import Vector
from externals.iterable_utils import difference, mag

def simulateGravitationalDynamics(
    f=None,
    ballList=[],
    initialForceVisual=5,
    initialMovement=5,
    velocities=None,
    staticList=None,
    showForces=True,
    t0=0,
    tf=2,
    render=None,
    allowZMovement=False,
    steps=1,
):
    """
    Takes a list of Ball objects and simulates a gravitational interaction between them
    by using Newton's law of universal gravitation.

    Args:
        f (Frame, optional): Frame object needed for rendering. Defaults to None.
        ballList (list, optional): list of Ball objects that interact with one
            another. Defaults to [].
        initialForceVisual (float, optional): how long the initial maximum force
            Vector should be. Defaults to 5.
        initialMovement (float, optional): how large the initial maximum acceleration
            should be (in units/second^2). Defaults to 5.
        velocities (list, optional): list of initial velocities where each velocity is
            a list of 3 elements (x-component, y-component, and z-component). Defaults
            to None, in which case the starting velocities of each are zero.
        staticList (list, optional): list as long as ballList, but of booleans that
            indicate for each ball whether or not it should be static or not. Defaults
            to None, in which case all are dynamic.
        showForces (bool, optional): whether or not to show the force Vectors acting on
            each of the Ball's. Defaults to True.
        t0 (float, optional): the initial time of the simulation. Defaults to 0.
        tf (float, optional): the final time of the simulation. Defaults to 2.
        render (bool, optional): whether or not to force a render if f.render is False.
            Defaults to None.
        allowZMovement (bool, optional): whether or not movement in the z-direction is
            allowable. Usually, it's a good idea to leave this False, since floating
            point errors can propagate and get worse over time in the z-direction.
            Defaults to False.
        steps (int, optional): The number of steps *in between* each frame for which
            extra calculations are performed. Usually, a single step per frame shift
            is good enough, but in situations that require great precision, increasing
            this number may be warranted. Defaults to 1.

    Raises:
        CustomError: Must pass in Frame() object.
        CustomError: len(ballList) must be greater than 2.
        CustomError: initialForceVisual must be greater than 0.
        CustomError: initialMovement must be greater than 0.
        CustomError: all objects in ballList must have mass property

    Returns:
        list: list of force Vectors that can then be modified/deleted as desired.
    """
    # some error checking
    if f == None:
        raise CustomError("Must pass in Frame() object even if render set to False")
    if render == None:
        render = f.render
    if len(ballList) < 2:
        raise CustomError("No dynamics to simulate...")
    if initialForceVisual <= 0:
        raise CustomError(
            "simulateGravitationalDynamics() requires initialForceVisual > 0"
        )
    if initialMovement <= 0:
        raise CustomError(
            "simulateGravitationalDynamics() requires initialMovement > 0"
        )
    # check for mass property of Ball() - can't simulate any gravity if you don't know the masses!
    for b in ballList:
        if not hasattr(b, "mass"):
            raise CustomError(
                "simulateGrav...() requires all objects in ballList to have mass property"
            )
    if velocities == None:
        # init velocities
        velocities = [[0, 0, 0]] * len(ballList)
    if staticList == None:
        staticList = [False] * len(ballList)
    while len(staticList) < len(ballList):
        staticList.append(False)
    # given the origins at each mass, compute the force due to each
    totalForces = []
    totalAccels = []
    for m1 in ballList:
        # initialize force on mass
        totalForce = [0, 0, 0]
        for m2 in ballList:
            if m1 == m2:
                pass
            else:
                # determine the force between m1 and m2
                positionVector = difference(m1.origin, m2.origin)
                tempScale = G_CONST * m1.mass * m2.mass / (mag(positionVector) ** 3)
                tempForce = [tempScale * ri for ri in positionVector]
                totalForce = [
                    totali + tempi for totali, tempi in zip(totalForce, tempForce)
                ]
        totalForces.append(totalForce)
        totalAccel = [totali / m1.mass for totali in totalForce]
        totalAccels.append(totalAccel)

    # determine the appropriate scaling factor for the acceleration and force vectors
    maximumForce = 0
    for vec in totalForces:
        if mag(vec) > maximumForce:
            maximumForce = mag(vec)
    forceScalingFactor = initialForceVisual / maximumForce

    maximumAccel = 0
    for vec in totalAccels:
        if mag(vec) > maximumAccel:
            maximumAccel = mag(vec)
    # based off of x = 1/2*a*t^2, where initialMovement occurs in one second
    # as a crappy approximation, the force is constant over the relevant time period
    accelScalingFactor = 2 * initialMovement / maximumAccel

    # initiate force vectors
    forceObjs = []
    if showForces:
        for i in range(len(totalForces)):
            vec = totalForces[i]
            visualForce = [veci * forceScalingFactor for veci in vec]
            forceObjs.append(
                Vector(
                    visualForce[0], visualForce[1], visualForce[2], ballList[i].origin
                )
            )
        f.multiplay(forceObjs, "fade", [[A2]], render=render)
    # now, move the masses based off of their accelerations and velocities
    tcurr = t0
    nextBase = 10
    newDt = dt / steps
    if tf <= 0:
        return forceObjs
    if render:
        f.start()
    else:
        f.temporaryRender()
    while tcurr < tf:
        for _ in range(steps):
            for i in range(len(ballList)):
                m1 = ballList[i]
                accel = totalAccels[i]
                vel = velocities[i]
                force = totalForces[i]
                if showForces:
                    forceVec = forceObjs[i]
                # move masses based on their current velocities
                if not staticList[i]:
                    dx = [veli * newDt for veli in vel]
                    if not allowZMovement:
                        dx = [dx[0], dx[1], 0]
                    m1.shift(dx[0], dx[1], dx[2])
                    if showForces:
                        forceVec.shift(dx[0], dx[1], dx[2])
            for i in range(len(ballList)):
                m1 = ballList[i]
                accel = totalAccels[i]
                vel = velocities[i]
                force = totalForces[i]
                if showForces:
                    forceVec = forceObjs[i]
                # update the forces, the accelerations, and the velocities
                # initialize force on mass
                totalForce = [0, 0, 0]
                for m2 in ballList:
                    if m1 == m2:
                        pass
                    else:
                        # determine the force between m1 and m2
                        positionVector = difference(m1.origin, m2.origin)
                        tempScale = (
                            G_CONST * m1.mass * m2.mass / (mag(positionVector) ** 3)
                        )
                        tempForce = [tempScale * ri for ri in positionVector]
                        totalForce = [
                            totali + tempi
                            for totali, tempi in zip(totalForce, tempForce)
                        ]
                totalForces[i] = totalForce
                totalAccels[i] = [totali / m1.mass for totali in totalForce]
                # update velocities and forceObjs[i]
                velocities[i] = [
                    veli + accelScalingFactor * a * newDt
                    for veli, a in zip(velocities[i], accel)
                ]
                visualForce = [veci * forceScalingFactor for veci in force]
                if showForces:
                    forceVec.transform(visualForce[0], visualForce[1], visualForce[2])
            tcurr = tcurr + newDt
        if render:
            f.r()
            if tcurr > nextBase:
                f.stop()
                f.start()
                nextBase += 10
    if render:
        f.stop()
    return forceObjs
