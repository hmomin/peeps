import numpy as np
import time
from collections import deque
from pprint import pprint
from traceback import format_stack
from constants import WHITE, BLACK, GOLDEN_ANGLE
from externals.iterable_utils import multiply, subtraction, addition

def colorCalculator(hex):
    """
    Converts an RGB hex string into a tuple of (R, G, B) values from 0 to 1.

    Args:
        hex (str): hex value of color.

    Returns:
        tuple: tuple (R, G, B) of values from 0 to 1.
    """
    # check for pound-sign
    if hex[0] == "#":
        hex = hex[1:]
    # first, convert hex to decimal
    r = hex[0:2]
    g = hex[2:4]
    b = hex[4:6]
    colors = []
    for color in (r, g, b):
        dec = int(color, 16)
        colors.append(dec)
    print("converted " + hex + " to RGB:")
    print(colors)
    colors.append(255)
    for i in range(4):
        colors[i] /= 255
    print(tuple(colors))
    return tuple(colors)

def timeFormatter(seconds, total=True):
    """Formats time to be more intuitive when printing.

    Args:
        seconds (float): input time
        total (bool, optional): whether or not this is the total time of the script.
            Defaults to True.
    """
    if not total:
        print(time.strftime("%I:%M:%S %p", time.localtime(seconds)))
    else:
        if seconds < 60:
            print("Total time: %.1f seconds" % seconds)
        else:
            print(
                time.strftime("Total time (HH:MM:SS) = %H:%M:%S", time.gmtime(seconds))
            )

def dimmer(leColor=WHITE, percentage=10):
    """Makes an input color dimmer to a certain percentage of the original color.

    Args:
        leColor (tuple, optional): 4-tuple that defines the input color. Defaults to
            WHITE.
        percentage (float, optional): percentage of original color. Defaults to 10.

    Returns:
        tuple: dimmed color.
    """
    frac = percentage / 100
    return (leColor[0] * frac, leColor[1] * frac, leColor[2] * frac, leColor[3])

def brighter(leColor=BLACK, percentage=10):
    """
    Makes an input color brighter by a certain percentage of the distance to the
    original color.

    Args:
        leColor (tuple, optional): 4-tuple that defines the input color. Defaults to
            BLACK.
        percentage (float, optional): percentage distance to white color. Defaults to 10.

    Returns:
        tuple: brighter color.
    """
    frac = percentage / 100
    # figure out the distance between each of the components to pure white
    dist = multiply(frac, subtraction(WHITE, leColor))
    return addition(dist, leColor)

def mergeColors(color1=WHITE, color2=WHITE):
    """Merges two colors by taking the average between them.

    Args:
        color1 (tuple, optional): 4-tuple that defines a color. Defaults to WHITE.
        color2 (tuple, optional): 4-tuple that defines a color. Defaults to WHITE.

    Returns:
        tuple: merged color.
    """
    newColor = [0, 0, 0, 1]
    for idx, i, j in zip(range(len(newColor)), color1, color2):
        newColor[idx] = (i + j) / 2
    return tuple(newColor)

def sphericalToCartesian(r=60, phi=0, theta=0):
    """Simple conversion from Spherical to Cartesian coordinates.

    Args:
        r (float, optional): r value in spherical coordinates. Defaults to 60.
        phi (float, optional): phi value in spherical coordinates. Defaults to 0.
        theta (float, optional): theta value in spherical coordinates. Defaults to 0.

    Returns:
        tuple: tuple of Cartsian coordinates.
    """
    return (
        r * np.sin(theta) * np.cos(phi),
        r * np.sin(theta) * np.sin(phi),
        r * np.cos(theta),
    )

def cartesianToSpherical(x=0, y=0, z=0):
    """Simple conversion from Cartesian to Spherical coordinates.

    Args:
        x (float, optional): x-value in Cartesian coordinates. Defaults to 0.
        y (float, optional): y-value in Cartesian coordinates. Defaults to 0.
        z (float, optional): z-value in Cartesian coordinates. Defaults to 0.

    Returns:
        tuple: tuple of Spherical coordinates.
    """
    r = np.sqrt(x ** 2 + y ** 2 + z ** 2)
    return (r, np.arctan2(y, x), np.arccos(np.clip(z / r, -1, 1)))

def computeRelativeNodes(nodes=[]):
    """
    Takes a list of absolute nodes and computes a list of relative nodes. Example:
    [
        (0, 0, 0),
        (0, 5, 0),
        (5, 5, 0),
        (5, 0, 0)
    ]
    turns into
    [
        (0, 0, 0),
        (0, 5, 0),
        (5, 0, 0),
        (0, -5, 0)
    ].

    Args:
        nodes (list, optional): list of nodes. Defaults to [].

    Returns:
        list: list of relative nodes.
    """
    # go through the nodes and just change the absolutes to relatives
    newNodes = []
    prev = nodes[0]
    for i, node in enumerate(nodes):
        if i == 0 or type(node) is not tuple:
            newNodes.append(node)
        else:
            diff = subtraction(node, prev)
            newNodes.append(diff)
        prev = node
    return newNodes

def computeAbsoluteNodes(nodes=[]):
    """
    Takes a list of relative nodes and computes a list of absolute nodes. Example:
    [
        (0, 0, 0),
        (0, 5, 0),
        (5, 0, 0),
        (0, -5, 0)
    ]
    turns into
    [
        (0, 0, 0),
        (0, 5, 0),
        (5, 5, 0),
        (5, 0, 0)
    ].

    Args:
        nodes (list, optional): list of nodes. Defaults to [].

    Returns:
        list: list of absolute nodes.
    """
    # go through the nodes and just change the relatives to absolutes
    newNodes = []
    curr = nodes[0]
    currStack = deque()
    for i, node in enumerate(nodes):
        if i == 0:
            newNodes.append(node)
            currStack.append(curr)
        elif type(node) is not tuple:
            newNodes.append(node)
            currStack.pop()
            curr = currStack[len(currStack) - 1]
        else:
            curr = addition(curr, node)
            newNodes.append(curr)
            currStack.append(curr)
    return newNodes

def prettyPrint(obj):
    """Pretty prints some object in Python.

    Args:
        obj (object): some object.
    """
    pprint(vars(obj))

def printCallStack():
    """
    Prints the current call stack. Useful for debugging purposes.
    """
    for line in format_stack():
        print(line.strip())

def sphericallyEquidistantPoints(radius=1, numPoints=100):
    """
    Generates roughly spherically equidistant points at some radius. Need this for
    lamp placement on non-emitting imported objects. The algorithm is a fibonacci
    spiral sphere algorithm - see here:
    https://bduvenhage.me/geometry/2019/07/31/generating-equidistant-vectors.html

    Args:
        radius (float, optional): radius of sphere containing points. Defaults to 1.
        numPoints (int, optional): number of points. Defaults to 100.

    Returns:
        list: list of nodes at each determined point.
    """
    points = numPoints * [False]
    for i in range(1, numPoints + 1):
        lat = np.arcsin(-1 + 2 * i / (numPoints + 1))
        lon = GOLDEN_ANGLE * i
        points[i - 1] = (
            radius * np.cos(lon) * np.cos(lat),
            radius * np.sin(lon) * np.cos(lat),
            radius * np.sin(lat),
        )
    return points
