import mathutils as mut
import numpy as np
from collections import deque
from constants import C, EASE_IN_OUT, ORIGIN, PI, CustomError, LINEAR
from externals.blender_utils import computeQuaternion
from externals.bezier_interpolation import interpolate
from externals.iterable_utils import addition, mag
from externals.miscellaneous import sphericalToCartesian, cartesianToSpherical

def camTransform():
    """
    Transforms the camera so that it points toward the world origin.
    """
    # always aims at origin
    cam = C.scene.camera
    # define new vector
    ogAxis = mut.Vector((0, 0, 1))
    newAxis = mut.Vector(cam.location)
    # perform quaternion rotation
    cam.rotation_quaternion = computeQuaternion(ogAxis, newAxis)

def camQuatTransform(loc=(0, 0, 60), quat=(1, 0, 0, 0)):
    """
    This is a very useful alternative to camTransform() - sometimes camTransform()
    leads to unexpected orientations. This works by just LERP'ing between two definite
    states of (location, quaternion)

    Args:
        loc (tuple, optional): desired location of camera. Defaults to (0, 0, 60).
        quat (tuple, optional): desired rotation_quaternion of camera. Defaults to
            (1, 0, 0, 0).
    """
    C.scene.camera.location = mut.Vector(loc)
    C.scene.camera.rotation_quaternion = mut.Quaternion(quat)
def init_camQuatTransform(
    t0=0, tf=2, rate=EASE_IN_OUT, loc=(0, 0, 60), quat=(1, 0, 0, 0)
):
    cam = C.scene.camera
    ogLoc = cam.location
    ogQuat = cam.rotation_quaternion
    t = interpolate(t0, tf, rate)
    t.pop(0)
    locs_0 = interpolate(ogLoc[0], loc[0], rate, len(t))
    locs_0.reverse()
    locs_1 = interpolate(ogLoc[1], loc[1], rate, len(t))
    locs_1.reverse()
    locs_2 = interpolate(ogLoc[2], loc[2], rate, len(t))
    locs_2.reverse()
    quats_0 = interpolate(ogQuat[0], quat[0], rate, len(t))
    quats_0.reverse()
    quats_1 = interpolate(ogQuat[1], quat[1], rate, len(t))
    quats_1.reverse()
    quats_2 = interpolate(ogQuat[2], quat[2], rate, len(t))
    quats_2.reverse()
    quats_3 = interpolate(ogQuat[3], quat[3], rate, len(t))
    quats_3.reverse()
    stack = deque()
    for loc0, loc1, loc2, quat0, quat1, quat2, quat3 in zip(
        locs_0, locs_1, locs_2, quats_0, quats_1, quats_2, quats_3
    ):
        stack.append((loc0, loc1, loc2, quat0, quat1, quat2, quat3))
    return stack
def update_camQuatTransform(val, loc=(0, 0, 60), quat=(1, 0, 0, 0)):
    newLoc = tuple(i for i in val[0:3])
    newQuat = tuple(i for i in val[3:7])
    camQuatTransform(newLoc, newQuat)

def camLoc(x=0, y=0, z=0, transform=True, xLam=None, yLam=None, zLam=None):
    """Changes the location of the camera in the scene.

    Args:
        x (float, optional): new x-location. Defaults to 0.
        y (float, optional): new y-location. Defaults to 0.
        z (float, optional): new z-location. Defaults to 0.
        transform (bool, optional): whether or not to point the camera towards the
            origin. Defaults to True.
        xLam (lambda, optional): lambda function that defines the x-shift
        transformation in time. Defaults to None.
        yLam (lambda, optional): lambda function that defines the y-shift
        transformation in time. Defaults to None.
        zLam (lambda, optional): lambda function that defines the z-shift
        transformation in time. Defaults to None.
    """
    cam = C.scene.camera
    cam.location = (x, y, z)
    if transform:
        camTransform()
def init_camLoc(
    t0=0,
    tf=1,
    rate=EASE_IN_OUT,
    x=0,
    y=0,
    z=0,
    transform=True,
    xLam=None,
    yLam=None,
    zLam=None,
):
    cam = C.scene.camera
    t = interpolate(t0, tf, rate)
    t.pop(0)
    ogAxis = mut.Vector(cam.location)
    newAxis = mut.Vector((x, y, z))
    v = (newAxis - ogAxis) / (tf - t0)
    if xLam == None or yLam == None or zLam == None:

        def xLam(t):  # pylint: disable=function-redefined
            return ogAxis[0] + (t - t0) * v[0]

        def yLam(t):  # pylint: disable=function-redefined
            return ogAxis[1] + (t - t0) * v[1]

        def zLam(t):  # pylint: disable=function-redefined
            return ogAxis[2] + (t - t0) * v[2]

    stack = deque()
    t.reverse()
    for tj in t:
        stack.append((xLam(tj), yLam(tj), zLam(tj)))
    return stack
def update_camLoc(val, x=0, y=0, z=0, transform=True, xLam=None, yLam=None, zLam=None):
    camLoc(*val, transform)

def camAngles(r=60, phi=0, theta=0, transform=True, rLam=None, pLam=None, tLam=None):
    """Similar to camLoc(), but with spherical coordinates.

    Args:
        r (float, optional): desired r-value for camera (distance from origin).
            Defaults to 60.
        phi (float, optional): desired phi value for camera (angle in x-y plane).
            Defaults to 0.
        theta (float, optional): desired theta value for camera (angle between r and
            z-axis). Defaults to 0.
        transform (bool, optional): determines whether or not to point the camera
            toward the origin. Defaults to True.
        rLam (lambda, optional): lambda function that defines how r evolves in time.
            Defaults to None.
        pLam (lambda, optional): lambda function that defines how phi evolves in time.
            Defaults to None.
        tLam (lambda, optional): lambda function that defines how theta evolves in time.
            Defaults to None.
    """
    # determine location from spherical coordinates
    camLoc(*sphericalToCartesian(r, phi, theta), transform)
def init_camAngles(
    t0=0,
    tf=1,
    rate=EASE_IN_OUT,
    r=60,
    phi=0,
    theta=0,
    transform=True,
    rLam=None,
    pLam=None,
    tLam=None,
):
    cam = C.scene.camera
    t = interpolate(t0, tf, rate)
    t.pop(0)
    ogAxis = mut.Vector(cartesianToSpherical(*cam.location))
    newAxis = mut.Vector((r, phi, theta))
    v = (newAxis - ogAxis) / (tf - t0)
    # default lambda is a SLERP between (x1, y1, z1) and (x2, y2, z2)
    if rLam == None or pLam == None or tLam == None:

        def rLam(t):  # pylint: disable=function-redefined
            return ogAxis[0] + (t - t0) * v[0]

        def pLam(t):  # pylint: disable=function-redefined
            return ogAxis[1] + (t - t0) * v[1]

        def tLam(t):  # pylint: disable=function-redefined
            return ogAxis[2] + (t - t0) * v[2]

    stack = deque()
    t.reverse()
    for tj in t:
        stack.append((rLam(tj), pLam(tj), tLam(tj)))
    return stack
def update_camAngles(
    val, r=60, phi=0, theta=0, transform=True, rLam=None, pLam=None, tLam=None
):
    camAngles(*val, transform)

def camRotate(axis=ORIGIN, angle=0, angleDeg=False):
    """Rotates the camera about some axis through some angle.

    Args:
        axis (tuple, optional): 3-tuple that defines axis of rotation. Defaults to
            ORIGIN.
        angle (float, optional): angle of rotation. Defaults to 0.
        angleDeg (bool, optional): whether or not angle is in degrees. Defaults to
            False, so radians is expected.

    Raises:
        CustomError: indeterminate quaternion rotation from rotating by 180 degrees.
    """
    cam = C.scene.camera
    # default: about its own axis
    if axis == ORIGIN:
        axis = cam.location
    if angleDeg:
        angle = angle * PI / 180
    # determine quaternion
    q = mut.Quaternion(axis, angle)
    # check for indeterminacy of q
    if q.magnitude == 0:
        raise CustomError(
            "Indeterminate Quaternion Rotation: make use of another rotation to interpolate between antiparallel states"
        )
    q.normalize()
    # perform quaternion rotation
    cam.rotation_quaternion = q @ cam.rotation_quaternion
def init_camRotate(t0=0, tf=1, rate=EASE_IN_OUT, axis=ORIGIN, angle=0, angleDeg=False):
    cam = C.scene.camera
    if axis == ORIGIN:
        axis = cam.location
    t = interpolate(t0, tf, rate)
    t.pop(0)
    diffs = np.diff(interpolate(0, angle, rate, numIntervals=len(t))).tolist()
    stack = deque()
    diffs.reverse()
    for smallAngle in diffs:
        stack.append(smallAngle)
    return stack
def update_camRotate(val, axis=ORIGIN, angle=0, angleDeg=False):
    cam = C.scene.camera
    if axis == ORIGIN:
        axis = cam.location
    if val is None:
        raise CustomError("val must be specified and passed into update_transform()")
    camRotate(axis, val, angleDeg)

def camShift(x=0, y=0, z=0, transform=True):
    """Shifts the camera in the scene by some x, y, and z amounts.

    Args:
        x (float, optional): x-shift of camera. Defaults to 0.
        y (float, optional): y-shift of camera. Defaults to 0.
        z (float, optional): z-shift of camera. Defaults to 0.
        transform (bool, optional): whether or not to point the camera towards the
            world origin. Defaults to True.
    """
    cam = C.scene.camera
    shiftAmt = (x, y, z)
    camLoc(*addition(cam.location, shiftAmt), transform)
def init_camShift(t0=0, tf=1, rate=EASE_IN_OUT, x=0, y=0, z=0, transform=True):
    cam = C.scene.camera
    shiftAmt = (x, y, z)
    newLoc = addition(cam.location, shiftAmt)
    t = interpolate(t0, tf, rate)
    t.pop(0)
    xDiffs = np.diff(interpolate(cam.location[0], newLoc[0], rate, len(t))).tolist()
    xDiffs.reverse()
    yDiffs = np.diff(interpolate(cam.location[1], newLoc[1], rate, len(t))).tolist()
    yDiffs.reverse()
    zDiffs = np.diff(interpolate(cam.location[2], newLoc[2], rate, len(t))).tolist()
    zDiffs.reverse()
    stack = deque()
    for xDiff, yDiff, zDiff in zip(xDiffs, yDiffs, zDiffs):
        stack.append((xDiff, yDiff, zDiff))
    return stack
def update_camShift(val, x=0, y=0, z=0, transform=True):
    camShift(*val, transform)

def sceneShift(x=0, y=0, z=0, transform=True):
    """
    Equivalent to camShift in the exact opposite direction (slightly more intuitive).

    Args:
        x (float, optional): x-shift of scene. Defaults to 0.
        y (float, optional): y-shift of scene. Defaults to 0.
        z (float, optional): z-shift of scene. Defaults to 0.
        transform (bool, optional): determines whether or not to point the camera
            towards the world origin. Defaults to True.
    """
    camShift(-x, -y, -z, transform)
def init_sceneShift(t0=0, tf=1, rate=EASE_IN_OUT, x=0, y=0, z=0, transform=True):
    return init_camShift(t0, tf, rate, -x, -y, -z, transform)
def update_sceneShift(val, x=0, y=0, z=0, transform=True):
    update_camShift(val, -x, -y, -z, transform)

def ambientHorizontalCameraRotation(f, runtime=8, stopAng=2 * PI):
    """Rotates the camera in the horizontal direction about the origin.

    Args:
        f (Frame): Frame object needed for rendering.
        runtime (float, optional): runtime of animation. Defaults to 8.
        stopAng (float, optional): total angle to rotate through. Defaults to 2*PI.
    """
    radius = mag(tuple(C.scene.camera.location))
    omega = stopAng / runtime
    zLam = lambda t, radius=radius, omega=omega: radius * np.cos(omega * t)
    xLam = lambda t, radius=radius, omega=omega: radius * np.sin(omega * t)
    yLam = lambda t: 0
    f.play(
        [camLoc],
        [[0, 0, 0, True, xLam, yLam, zLam]],
        tf=runtime,
        rate=LINEAR,
        testRender=True,
    )
