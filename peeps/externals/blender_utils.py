import mathutils as mut
import os
from constants import C, D, CustomError, EXT_DIR, WHITE_GRAY
from externals.iterable_utils import flatten

def selectOnly(strList=[], all=False):
    """Selects only the objects in the UI with names in strList

    Args:
        strList (list, optional): list of Blender objects to select. Defaults to [].
        all (bool, optional): if True, the function ignores strList and just selects
            all of the objects in the UI. Defaults to False.
    """
    # adjust if strList not a list
    if type(strList) is not list:
        strList = [strList]
    if not all:
        for obj in D.objects:
            found = False
            for str in strList:
                if obj.name == str:
                    found = True
                    obj.select_set(True)
                    C.view_layer.objects.active = D.objects[str]
                    break
            if not found:
                obj.select_set(False)
    else:
        for obj in D.objects:
            obj.select_set(True)

def computeQuaternion(v1, v2):
    """Computes the quaternion between two mathutils Vectors.

    Args:
        v1 (mathutils.Vector): First mathutils Vector.
        v2 (mathutils.Vector): Second mathutils Vector.

    Raises:
        CustomError: indeterminate quaternion between two antiparallel vectors.

    Returns:
        mathutils.Quaternion: the resultant Quaternion
    """
    q = mut.Quaternion((0, 0, 0, 0))
    v3 = v1.cross(v2)
    for j in range(1, 4):
        q[j] = v3[j - 1]
    q[0] = v1.length * v2.length + v1.dot(v2)
    # check for indeterminacy of q
    if q.magnitude == 0:
        raise CustomError(
            "Indeterminate Quaternion Rotation: make use of another rotation to interpolate between antiparallel states"
        )
    q.normalize()
    return q

def delete(objList):
    """Deletes all the Blobjects in objList by calling delete() on all of them

    Args:
        objList (list): list of Blobjects
    """
    # error checking
    if not isinstance(objList, list):
        objList = [objList]
    objList = flatten(objList)
    for obj in objList:
        obj.delete()

def import_blend(filename, objNames=[]):
    """Import object(s) from an external blend file.

    Args:
        filename (str): name of .blend file that contains external object.
        objNames (list, optional): names of objects to be imported from file.
            Defaults to [].

    Returns:
        list: list of objects imported from external blend file.
    """
    # error check for filename
    if not filename.endswith(".blend"):
        filename += ".blend"
    with D.libraries.load(os.path.join(EXT_DIR, filename)) as (data_from, data_to):
        for name in data_from.objects:
            for checkName in objNames:
                if name.startswith(checkName):
                    data_to.objects.append(name)
    for obj in data_to.objects:
        if obj is not None:
            C.collection.objects.link(obj)
    return data_to.objects

def changeBackgroundColor(color=WHITE_GRAY):
    """Changes the background color in the UI.

    Args:
        color (tuple, optional): 4-tuple that defines new color. Defaults to
            WHITE_GRAY.

    Returns:
        bool: True
    """
    C.scene.world.node_tree.nodes["Background"].inputs["Color"].default_value = color
    return True
