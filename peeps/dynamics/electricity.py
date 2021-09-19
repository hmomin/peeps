import mathutils as mut
import numpy as np
from constants import CustomError, K_COULOMB, dt, A2
from blobjects.shapes import Vector
from externals.iterable_utils import difference, mag, addition, subtraction

def computeElectricAccelerations(chargeList=[], scale=1):
    """Determines the accelerations for some charge configuration in space.

    Args:
        chargeList (list, optional): list of charges. Defaults to [].
        scale (float, optional): scaling factor applied to all accelerations.
            Defaults to 1.

    Raises:
        CustomError: length of chargeList must be greater than 2.
        CustomError: all objects in chargeList must have mass and charge properties.

    Returns:
        list: list of accelerations, each of which is a list of three elements
            (x-acceleration, y-acceleration, z-acceleration)
    """
    # error checking
    if len(chargeList) < 2:
        raise CustomError("No dynamics to simulate...")
    scale = np.abs(scale)
    # check for mass and charge properties in charges - to properly simulate dynamics
    for c in chargeList:
        if not hasattr(c, "mass") or not hasattr(c, "charge"):
            raise CustomError(
                "computeElectricAccelerations() requires all objects in chargeList to have mass and charge properties"
            )
    # given the origins at each charge, compute the force due to each
    totalForces = []
    totalAccels = []
    for q1 in chargeList:
        # initialize force on charge
        totalForce = [0, 0, 0]
        for q2 in chargeList:
            if q1 == q2:
                pass
            else:
                # determine the force between q1 and q2
                positionVector = difference(q1.origin, q2.origin)
                tempScale = (
                    -K_COULOMB * q1.charge * q2.charge / (mag(positionVector) ** 3)
                )
                tempForce = [tempScale * ri for ri in positionVector]
                totalForce = [
                    totali + tempi for totali, tempi in zip(totalForce, tempForce)
                ]
        totalForces.append(totalForce)
        totalAccel = [i / q1.mass for i in totalForce]
        totalAccels.append(totalAccel)
    return [[i * scale for i in temp] for temp in totalAccels]
def updateChargeVelocitiesAccelerations(chargeList=[], scale=1):
    """
    Updates the charge velocities and accelerations given the current configuration
    in space.

    Args:
        chargeList (list, optional): list of PointCharge objects. Defaults to [].
        scale (float, optional): a scaling factor applied to the accelerations of
            all charge objects. Defaults to 1.
    """
    for c, a in zip(chargeList, computeElectricAccelerations(chargeList, scale)):
        c.acceleration = a
        if not hasattr(c, "velocity"):
            c.velocity = [0, 0, 0]
        else:
            c.velocity = [vi + ai * dt for vi, ai in zip(c.velocity, a)]
def simulateElectrodynamics(
    f=None,
    chargeList=[],
    initialForceVisual=5,
    initialMovement=5,
    velocities=None,
    staticList=None,
    showForces=True,
    t0=0,
    tf=2,
    render=None,
    constrained=False,
    constraintOrigin=(0, 0, 0),
    constraintRadius=1,
    allowZMovement=False,
):
    """
    Takes a list of PointCharge objects and simulates an electrical interaction
    between them by using Coulomb's law.

    Args:
        f (Frame, optional): Frame object needed for rendering. Defaults to None.
        chargeList (list, optional): list of PointCharge objects that interact with
            one another. Defaults to [].
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
        constrained (bool, optional): whether the PointCharge objects are constrained
            within a radial domain of constraint. Defaults to False.
        constraintOrigin (tuple, optional): center of radial domain of constraint.
            Defaults to (0, 0, 0).
        constraintRadius (int, optional): radius of constraining domain. Defaults to 1.
        allowZMovement (bool, optional): whether or not movement in the z-direction is
            allowable. Usually, it's a good idea to leave this False, since floating
            point errors can propagate and get worse over time in the z-direction.
            Defaults to False.

    Raises:
        CustomError: Must pass in Frame() object.
        CustomError: len(chargeList) must be greater than 2.
        CustomError: initialForceVisual must be greater than 0.
        CustomError: initialMovement must be greater than 0.
        CustomError: all objects in chargeList must have mass and charge properties.

    Returns:
        list: list of force Vectors that can then be modified/deleted as desired.
    """
    # some error checking
    if f == None:
        raise CustomError("Must pass in Frame() object even if render set to False")
    if render == None:
        render = f.render
    if len(chargeList) < 2:
        raise CustomError("No dynamics to simulate...")
    if initialForceVisual <= 0:
        raise CustomError("simulateElectrodynamics() requires initialForceVisual > 0")
    if initialMovement <= 0:
        raise CustomError("simulateElectrodynamics() requires initialMovement > 0")
    # check for mass and charge properties in charges - to properly simulate dynamics
    for c in chargeList:
        if not hasattr(c, "mass") or not hasattr(c, "charge"):
            raise CustomError(
                "simulateElectrodynamics() requires all objects in chargeList to have mass and charge properties"
            )
    if velocities == None:
        # init velocities
        velocities = [[0, 0, 0]] * len(chargeList)
    if staticList == None:
        staticList = [False] * len(chargeList)
    while len(staticList) < len(chargeList):
        staticList.append(False)
    # given the origins at each charge, compute the force due to each
    totalForces = []
    totalAccels = []
    for q1 in chargeList:
        # initialize force on charge
        totalForce = [0, 0, 0]
        for q2 in chargeList:
            if q1 == q2:
                pass
            else:
                # determine the force between q1 and q2
                positionVector = difference(q1.origin, q2.origin)
                tempScale = (
                    -K_COULOMB * q1.charge * q2.charge / (mag(positionVector) ** 3)
                )
                tempForce = [tempScale * ri for ri in positionVector]
                totalForce = [
                    totali + tempi for totali, tempi in zip(totalForce, tempForce)
                ]
        totalForces.append(totalForce)
        totalAccel = [i / q1.mass for i in totalForce]
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
                    visualForce[0], visualForce[1], visualForce[2], chargeList[i].origin
                )
            )
        f.multiplay(forceObjs, "fade", [[A2]], render=render)
    # now, move the charges based off of their accelerations and velocities
    tcurr = t0
    if tf <= 0:
        return forceObjs
    if render:
        f.start()
    else:
        f.temporaryRender()
    while tcurr < tf:
        for i in range(len(chargeList)):
            q1 = chargeList[i]
            accel = totalAccels[i]
            vel = velocities[i]
            force = totalForces[i]
            if showForces:
                forceVec = forceObjs[i]
            # move charges based on their current velocities
            if not staticList[i]:
                dx = [veli * dt for veli in vel]
                # check if dx would push the charge over the boundary
                if constrained:
                    newSpot = addition(dx, q1.origin)
                    newRadius = subtraction(newSpot, constraintOrigin)
                    if mag(newRadius) > constraintRadius:
                        # determine the parallel component of movement,
                        # i.e. the perpendicular of dx with respect to some radial vector
                        mutDx = mut.Vector(tuple(dx))
                        mutRadius = mut.Vector(tuple(newRadius))
                        unitVec = mutRadius.normalized()
                        # turn dx into the parallel-to-surface / perp-to-radius version
                        dx = mutDx - (mutDx.dot(unitVec)) * unitVec
                        if not allowZMovement:
                            dx = [dx[0], dx[1], 0]
                        # do a final check for movement beyond the boundary - can happen because of small
                        # perpendicular movements creating an outward spiral
                        newSpot = addition(dx, q1.origin)
                        newRadius = subtraction(newSpot, constraintOrigin)
                        if mag(newRadius) > constraintRadius:
                            # determine the projection between here and the edge that's less than the radius
                            mutRadius = mut.Vector(tuple(newRadius))
                            # find a radius within constraint - prefer to move here instead
                            preferredRadius = mutRadius.normalized() * constraintRadius
                            dx = subtraction(preferredRadius, q1.origin)
                            if not allowZMovement:
                                dx = [dx[0], dx[1], 0]
                q1.shift(dx[0], dx[1], dx[2])
                if showForces:
                    forceVec.shift(dx[0], dx[1], dx[2])
        for i in range(len(chargeList)):
            q1 = chargeList[i]
            accel = totalAccels[i]
            vel = velocities[i]
            force = totalForces[i]
            if showForces:
                forceVec = forceObjs[i]
            # update the forces, the accelerations, and the velocities
            # initialize force on charge
            totalForce = [0, 0, 0]
            for q2 in chargeList:
                if q1 == q2:
                    pass
                else:
                    # determine the force between q1 and q2
                    positionVector = difference(q1.origin, q2.origin)
                    tempScale = (
                        -K_COULOMB * q1.charge * q2.charge / (mag(positionVector) ** 3)
                    )
                    tempForce = [tempScale * ri for ri in positionVector]
                    totalForce = [
                        totali + tempi for totali, tempi in zip(totalForce, tempForce)
                    ]
            totalForces[i] = totalForce
            totalAccels[i] = [totali / q1.mass for totali in totalForce]
            # update velocities and forceObjs[i]
            velocities[i] = [
                veli + accelScalingFactor * a * dt
                for veli, a in zip(velocities[i], accel)
            ]
            visualForce = [veci * forceScalingFactor for veci in force]
            if showForces:
                forceVec.transform(visualForce[0], visualForce[1], visualForce[2])
        tcurr = tcurr + dt
        if render:
            f.r()
    if render:
        f.stop()
    return forceObjs
