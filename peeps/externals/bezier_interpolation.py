import numpy as np
import sys
from constants import EASE, CustomError, FRAME_RATE, PI,\
    BLACK, WHITE, MAKE_LIGHT, MAKE_DARK

def cubic_bezier(tPoints=[0], inPoints=EASE):
    """
    Converts a list of floats (tPoints) into a new list that has those floats conform
    to some Bezier-curve defined rate.

    Args:
        tPoints (list, optional): list of values that are linearly spaced from one
            another. Defaults to [0].
        inPoints (tuple, optional): Bezier-curve defined rate. Defaults to EASE.

    Raises:
        CustomError: inPoints must be a 4-tuple.

    Returns:
        list: new list of points with Bezier-curve rate applied
    """
    # error checking for nothing happening...
    if tPoints[0] == tPoints[-1]:
        return tPoints
    # inPoints must be a 4-tuple
    if type(inPoints) is not tuple or len(inPoints) != 4:
        raise CustomError("input to cubic_bezier() must be a 4-tuple")
    # map t to go from 0 to 1
    # note: this expects tPoints to be linearly spaced
    a = 1 / (tPoints[-1] - tPoints[0])
    b = -tPoints[0] / (tPoints[-1] - tPoints[0])
    mappedtPoints = [a * ti + b for ti in tPoints]
    tNewMapped = []
    for ti in mappedtPoints:
        (x1, y1, x2, y2) = inPoints
        """
        basing algorithm off of:
        https://stackoverflow.com/questions/8217346/cubic-bezier-curves-get-y-for-given-x
        X(t) = (1-t)^3 * X0 + 3*(1-t)^2 * t * X1 + 3*(1-t) * t^2 * X2 + t^3 * X3
        Y(t) = (1-t)^3 * Y0 + 3*(1-t)^2 * t * Y1 + 3*(1-t) * t^2 * Y2 + t^3 * Y3
        """
        # first, determine value of t for which X is equal to the input t
        leRoots = np.roots([1 + 3 * x1 - 3 * x2, -6 * x1 + 3 * x2, 3 * x1, -ti])
        timeRoots = []
        eps = 0.000001
        for root in leRoots:
            if np.isreal(root) and root <= 1 + eps and root >= -eps:
                timeRoots.append(root.real)
        # error checking for none (due to roundoff error)
        if len(timeRoots) == 0:
            minVal = sys.maxsize
            for root in leRoots:
                if (
                    root.real <= 1 + eps
                    and root.real >= -eps
                    and abs(root.imag) < minVal
                ):
                    minRoot = root
                    minVal = abs(root.imag)
            timeRoots.append(minRoot.real)
        t1 = timeRoots[0]
        tNewMapped.append(
            3 * (1 - t1) ** 2 * t1 * y1 + 3 * (1 - t1) * t1 ** 2 * y2 + t1 ** 3
        )
    # undo t mapping
    return [(ti - b) / a for ti in tNewMapped]

def interpolate(xi=0, xf=1, rate=EASE, numIntervals=-1):
    """Interpolates between xi and xf with a Bezier-curve based rate.

    Args:
        xi (float, optional): beginning point of interpolation. Defaults to 0.
        xf (float, optional): ending point of interpolation. Defaults to 1.
        rate (tuple, optional): Bezier-curve defined rate. Defaults to EASE.
        numIntervals (int, optional): number of intervals between each point.
            Defaults to -1.

    Raises:
        CustomError: numIntervals must be greater than 1

    Returns:
        list: interpolated list of values with Bezier-curve rate applied
    """
    # determine t values
    if numIntervals == -1:
        t = np.linspace(xi, xf, (xf - xi) * FRAME_RATE + 1)
    elif numIntervals < 1:
        raise CustomError("numIntervals is less than 1")
    elif xi == xf:
        return [xi] * (numIntervals + 1)
    else:
        t = np.linspace(xi, xf, numIntervals + 1)
    # return corrected t via bezier
    return cubic_bezier(t, rate)

def sine_interpolate(A=1, T=4, runtime=-1):
    """
    Creates a list of points interpolated among all frames of a time period via a
    sine function that has no phase shift.

    Args:
        A (float, optional): amplitude of the sine wave interpolation. Defaults to 1.
        T (float, optional): time period of sine wave interpolation. Defaults to 4.
        runtime (float, optional): runtime of animation. Defaults to T.

    Raises:
        CustomError: runtime must be greater than 1.

    Returns:
        list: list of interpolated points.
    """
    x = lambda t, A=A, T=T: A * np.sin(2 * PI * t / T)
    if runtime == -1:
        runtime = T
    elif runtime < 1:
        raise CustomError("runtime is less than 1")
    tVals = [i / FRAME_RATE for i in range(runtime * FRAME_RATE)]
    return [x(t) for t in tVals]

def cosine_interpolate(A=1, T=4, runtime=-1):
    """
    Creates a list of points interpolated among all frames of a time period via a
    cosine function that has no phase shift.

    Args:
        A (float, optional): amplitude of the cosine wave interpolation. Defaults to 1.
        T (float, optional): time period of cosine wave interpolation. Defaults to 4.
        runtime (float, optional): runtime of animation. Defaults to T.

    Raises:
        CustomError: runtime must be greater than 1.

    Returns:
        list: list of interpolated points.
    """
    x = lambda t, A=A, T=T: A * np.cos(2 * PI * t / T)
    if runtime == -1:
        runtime = T
    elif runtime < 1:
        raise CustomError("runtime is less than 1")
    tVals = [i / FRAME_RATE for i in range(runtime * FRAME_RATE)]
    return [x(t) for t in tVals]

def lerp_constants(p1=(0, 1), p2=(5, 10)):
    """
    If f(x) = a*x + b is the line that connects p1(x, y) and p2(x, y), what are the
    constants x and y?

    Args:
        p1 (tuple, optional): First point (x, y). Defaults to (0, 1).
        p2 (tuple, optional): Second point (x, y). Defaults to (5, 10).

    Raises:
        CustomError: p1 and p2 must be tuples of length 2 each.
        CustomError: line cannot be vertical.

    Returns:
        tuple: (a, b) returned as a tuple
    """
    # error checking
    if len(p1) != 2 or len(p2) != 2:
        raise CustomError("p1 and p2 must have a length of 2 each")
    (x1, y1) = p1
    (x2, y2) = p2
    # error checking for x1 == x2
    if x1 == x2:
        raise CustomError("x1 must not equal x2 - this is a vertical line...")
    a = (y2 - y1) / (x2 - x1)
    b = (x2 * y1 - x1 * y2) / (x2 - x1)
    return (a, b)

def getInterpolatedColors(ti=0, tf=1, colori=BLACK, colorf=WHITE, rate=EASE):
    """
    Interpolates between colori and colorf using a Bezier-curve defined rate.
    The speed/length of the interpolation is determined by (tf - ti).

    Args:
        ti (float, optional): starting time of interpolation. Defaults to 0.
        tf (float, optional): ending time of interpolation. Defaults to 1.
        colori (tuple, optional): initial color. Defaults to BLACK.
        colorf (tuple, optional): final color. Defaults to WHITE.
        rate (tuple, optional): Bezier-curve defined rate. Defaults to EASE.

    Returns:
        list: list of (t, (R, G, B, 1)) pairs for each frame.
    """
    # change the rate if fading from black or to black
    if colori == BLACK:
        rate = MAKE_LIGHT
    elif colorf == BLACK:
        rate = MAKE_DARK
    # determine the time values
    tAdj = interpolate(ti, tf, rate)
    tAdj.pop(0)
    colorR = interpolate(colori[0], colorf[0], rate, len(tAdj))
    colorR.pop(0)
    colorG = interpolate(colori[1], colorf[1], rate, len(tAdj))
    colorG.pop(0)
    colorB = interpolate(colori[2], colorf[2], rate, len(tAdj))
    colorB.pop(0)
    colors = [(tAdj[i], (colorR[i], colorG[i], colorB[i], 1)) for i in range(len(tAdj))]
    return colors