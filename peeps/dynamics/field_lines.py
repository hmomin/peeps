import math
import mathutils as mut
import numpy as np
from constants import CustomError, PI, LINEAR, K_COULOMB, A3
from blobjects.shapes import FieldLine
from externals.bezier_interpolation import interpolate
from externals.blender_utils import delete
from externals.iterable_utils import addition, difference

# only supports 2D for now...
def generateFieldLines(
    chargeList=[],
    lengthList=[100],
    numFactor=4,
    ds=0.1,
    boundingBox=[(-21.5, -12), (21.5, 12)],
    margin=0.5,
    initialData=None,
):
    """A 2D generation of electric field lines as a result of some list of charges.

    Args:
        chargeList (list, optional): list of PointCharge objects. Defaults to [].
        lengthList (list, optional): list of maximum length of field line for each
            individual charge. Defaults to [100].
        numFactor (int, optional): number of field lines per charge. Defaults to 4.
        ds (float, optional): the step-size or distance to traverse for each
            field line coordinate before calculating the next direction. Defaults to
            0.1.
        boundingBox (list, optional): bounds the field lines from exiting the box.
            boundingBox takes the form [(left, bottom), (right, top)]. Defaults to
            [(-21.5, -12), (21.5, 12)].
        margin (float, optional): an extra margin to prevent the field lines from
            straying outside the boundingBox. Defaults to 0.5.
        initialData (list, optional): previously returned data concerning field lines.
            Defaults to None.

    Raises:
        CustomError: boundingBox must be a list of two xy tuples like
            [(bottom-left corner), (top-right corner)].

    Returns:
        list: a complicated list of data regarding the field lines that can be passed
            back into this function.
    """
    # error checking
    if numFactor < 0:
        numFactor = 1
    if type(chargeList) is not list:
        chargeList = [chargeList]
    if type(lengthList) is not list:
        lengthList = [lengthList]
    if type(boundingBox) is not list:
        raise CustomError(
            "expect boundingBox to be a list of two xy tuples: [(bottom-left corner), (top-right corner)]"
        )
    while len(chargeList) > len(lengthList):
        lengthList.append(lengthList[-1])
    # relevant enums
    LEFT = boundingBox[0][0] + margin
    BOTTOM = boundingBox[0][1] + margin
    RIGHT = boundingBox[1][0] - margin
    TOP = boundingBox[1][1] - margin
    leFieldLines = []
    leCharges = [np.abs(c.charge) for c in chargeList]
    newCurveData = []
    leMin = leCharges[0]
    for c in leCharges:
        if c < leMin:
            leMin = c
    leFactors = [round(c / leMin * numFactor) for c in leCharges]
    leMaxLength = 0
    dataCounter = 0
    # determine the true numFactors for each charge based off of the magnitudes of charges
    for c, leLength, leFactor in zip(chargeList, lengthList, leFactors):
        angs = interpolate(0, 2 * PI, LINEAR, leFactor)
        angs.pop()
        # init field lines in the direction of ang
        for ang in angs:
            currLength = 0
            # first coordinate
            if c.charge > 0:
                leRadius = c.radius
            else:
                leRadius = c.radius + margin
            if initialData and initialData[dataCounter]:
                coords, currLength, previousField = initialData[dataCounter]
                if c.charge < 0:
                    coords.reverse()
            else:
                coords = [
                    addition(
                        c.origin, (leRadius * np.cos(ang), leRadius * np.sin(ang), 0)
                    )
                ]
            dataCounter += 1
            # determine coords from here to either
            # a hit on another charge (within charge's radius + margin) or
            # a hit on the bounding box
            endy = coords[-1]
            if not initialData:
                previousField = None
            while (
                endy[0] > LEFT
                and endy[0] < RIGHT
                and endy[1] < TOP
                and endy[1] > BOTTOM
            ):
                # determine a normalized electric field at endy
                eField = mut.Vector((0, 0, 0))
                for q in chargeList:
                    rVec = mut.Vector(tuple(difference(q.origin, endy)))
                    magField = K_COULOMB * q.charge / rVec.length_squared
                    eField += magField * rVec.normalized()
                # move a distance of ds in the direction of the electric field
                distToMove = np.sign(c.charge) * ds * eField.normalized()
                # check if line has hit a point charge
                chargeHit = False
                for q in chargeList:
                    diffVec = mut.Vector(tuple(difference(q.origin, endy)))
                    if q.charge > 0:
                        checkLength = q.radius
                    else:
                        checkLength = q.radius + margin
                    if diffVec.magnitude <= checkLength and currLength > checkLength:
                        chargeHit = True
                        break
                if chargeHit:
                    break
                # check if eField near a stable sink
                if previousField == None:
                    previousField = eField.normalized()
                angBetween = np.arccos(
                    np.clip(eField.normalized().dot(previousField), -1, 1)
                )
                if not math.isnan(angBetween) and angBetween > 1:  # radians
                    break
                previousField = eField.normalized()
                # all checks are good, so append the new point to coords
                coords.append(tuple(addition(coords[-1], distToMove)))
                currLength += ds
                if currLength > leLength:
                    break
                # this is the new endy
                endy = coords[-1]
            if c.charge < 0:
                coords.reverse()
            if currLength > leMaxLength:
                leMaxLength = currLength
            newCurveData.append((coords, currLength, previousField))
            leFieldLines.append(FieldLine(coords))
    return (leFieldLines, leMaxLength, newCurveData)
def playFieldLines(f=None, dLength=0.1, chargeList=[], numFactor=4, render=None):
    """Helper function for animating field line generation via generateFieldLines().

    Args:
        f (Frame, optional): Frame object needed for rendering. Defaults to None.
        dLength (float, optional): change in length between frames and field line
            direction calculations. Defaults to 0.1.
        chargeList (list, optional): list of PointCharge objects. Defaults to [].
        numFactor (int, optional): number of field lines per charge. Defaults to 4.
        render (bool, optional): whether or not to force a render. Defaults to None.

    Raises:
        CustomError: Frame object must be passed in.

    Returns:
        list: list of FieldLine objects that can be modified or deleted as desired.
    """
    if f == None:
        raise CustomError("playFieldLines(): must pass in frame object")
    if render == None:
        render = f.render
    runningLength = 0.1
    oldLength = 0
    newLength = 0.1
    curveData = None
    if render:
        f.start()
    while oldLength != newLength:
        oldLength = newLength
        if curveData:
            fieldLines, maxLength, curveData = generateFieldLines(
                chargeList, [runningLength], numFactor, initialData=curveData
            )
        else:
            fieldLines, maxLength, curveData = generateFieldLines(
                chargeList, [runningLength], numFactor
            )
        newLength = maxLength
        print(
            "playFieldLines() maxLength so far: ",
            "{:4.1f}".format(round(maxLength / dLength) * dLength),
        )
        for lin in fieldLines:
            lin.color(A3)
        runningLength += dLength
        if render:
            f.r()
        if oldLength != newLength:
            delete(fieldLines)
    if render:
        f.stop()
    return fieldLines
