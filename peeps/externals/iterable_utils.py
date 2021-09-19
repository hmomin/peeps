import collections
import numpy as np

def mag(vec):
    """Determines the Euclidean norm of a vector in iterable form.

    Args:
        vec (iterable): some iterable that contains components.

    Returns:
        float: the Euclidean norm of the input.
    """
    leSum = 0
    for i in range(len(vec)):
        leSum += vec[i] ** 2
    return np.sqrt(leSum)

def difference(v1, v2):
    """Returns the difference between two vectors in iterable form, i.e. v2 - v1.

    Args:
        v1 (iterable): some vector.
        v2 (iterable): some vector.

    Returns:
        iterable: the resultant vector.
    """
    if type(v1) == tuple and type(v2) == tuple:
        return tuple(np.subtract(v2, v1))
    else:
        return [ai - bi for ai, bi in zip(v2, v1)]

def subtraction(v1, v2):
    """
    Just difference(), but in reverse, i.e. v1 - v2. Much more intuitive and this is a
    non-breaking change.

    Args:
        v1 (iterable): some vector.
        v2 (iterable): some vector.

    Returns:
        iterable: the resultant vector.
    """
    return difference(v2, v1)

def addition(v1, v2):
    """Returns the addition of two vectors in iterable form, i.e. v1 + v2.

    Args:
        v1 (iterable): some vector.
        v2 (iterable): some vector.

    Returns:
        iterable: the resultant vector.
    """
    if type(v1) == tuple and type(v2) == tuple:
        return tuple(np.add(v1, v2))
    else:
        return [ai + bi for ai, bi in zip(v2, v1)]

def multiply(k, v1):
    """Returns the k*v1 where k is multiplied by each element in v1.

    Args:
        k (float): scale factor.
        v1 (iterable): a vector in iterable form.

    Returns:
        iterable: the resultant vector.
    """
    newIterable = [k * i for i in v1]
    return tuple(newIterable) if type(v1) == tuple else newIterable

def negate(vec):
    """Negates a vector in iterable form.

    Args:
        vec (iterable): a vector iterable.

    Returns:
        iterable: the resultant vector.
    """
    if type(vec) == tuple:
        return tuple([-i for i in vec])
    else:
        return [-i for i in vec]

def flatten(someList):
    """
    Flattens a nested list into a list with singular elements. Example:
    [[[0, 1, 3], [4, 7]], [0, 1], 2]
    turns into
    [0, 1, 3, 4, 7, 0, 1, 2]

    Args:
        someList (iterable): a nested list or iterable.

    Returns:
        list: the flattened version of the list.
    """
    if isinstance(someList, collections.Iterable):
        return [a for i in someList for a in flatten(i)]
    else:
        return [someList]

def flattenOnce(someList):
    """Only flattens a list by one level. Example:
    [[[0, 1, 3], [4, 7]], [0, 1], 2]
    turns into
    [[0, 1, 3], [4, 7], 0, 1, 2].

    Args:
        someList (iterable): a nested iterable.

    Returns:
        list: resultant list.
    """
    newList = []
    for i in someList:
        if isinstance(i, collections.Iterable):
            for j in i:
                newList.append(j)
        else:
            newList.append(i)
    return newList

def deepenOnce(someList):
    """Deepens list by one level. Example:
    [0, 1, 2, 3, 4, 5]
    turns into
    [[0], [1], [2], [3], [4], [5]]

    Args:
        someList (iterable): some iterable.

    Returns:
        list: deepened resultant list
    """
    return [[a] for a in someList]

def alternator(iterable, frontFirst=True):
    """
    Alternates an iterable from front to back and returns the alternation as a list.
    Example:
    [0, 1, 2, 3, 4, 5]
    turns into
    [0, 5, 1, 4, 2, 3] if frontFirst is True and
    [5, 0, 4, 1, 3, 2] if frontFirst is False.

    Args:
        iterable (iterable): some iterable to alternate.
        frontFirst (bool, optional): whether to use the front element first or the
            back element first. Defaults to True, so front element first.

    Returns:
        list: the alternated iterable.
    """
    res = iterable.copy()
    idx = 0
    flipper = frontFirst
    while len(iterable) > 0:
        if flipper:
            res[idx] = iterable.pop(0)
        else:
            res[idx] = iterable.pop(-1)
        flipper = not flipper
        idx += 1
    return res

def splitByMax(iterable):
    """
    Takes a list of nodes and spits out that same list reordered by choosing the first
    node and maximizing the distance to subsequent nodes.

    Args:
        iterable (iterable): a list of nodes.

    Returns:
        list: the list reordered by maximizing distances to subsequent nodes.
    """
    ogLen = len(iterable)
    # create a 2D-list of all the distances to each node
    matrix = [[0 for x in range(ogLen)] for y in range(ogLen)]
    for i, a in enumerate(iterable):
        for j, b in enumerate(iterable):
            matrix[i][j] = mag(subtraction(a, b))
    # gotta start somewhere, so start at the top of the list
    currentSet = [0]
    sums = ogLen * [0]
    while len(currentSet) < ogLen:
        # determine the next spot by examining the sums of distances
        for i in range(ogLen):
            if i in currentSet:
                sums[i] = 0
            else:
                sums[i] += matrix[i][currentSet[-1]]
        newIdx = sums.index(max(sums))
        currentSet.append(newIdx)
    return [iterable[i] for i in currentSet]
