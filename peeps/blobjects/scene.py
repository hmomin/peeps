import bpy # pylint: disable=import-error
from constants import C, D, ORIGIN
from blobjects.blobject import Blobject

class Camera(Blobject):
    def __init__(self, location=(0, 0, 60), normal=(0, 0, 1)):
        """
        Creates camera for scene. You shouldn't need to call this manually.

        Args:
            location (tuple, optional): Origin of camera. Defaults to (0, 0, 60).
            normal (tuple, optional): Direction directly opposite to the direction
                the camera points in. Defaults to (0, 0, 1).
        """
        bpy.ops.object.camera_add(location=location)
        C.scene.camera = C.object
        self.normal = (0, 0, 1)
        self.origin = location
        self.name = ["Camera"]
        self.transform(normal)
        bpy.ops.object.origin_set(type="ORIGIN_CURSOR", center="MEDIAN")

class Lamp(Blobject):
    def __init__(self, location=ORIGIN, energy=50):
        """
        Creates a lamp that lights up certain aspects of the scene, but is
        invisible in renders (i.e. the lighting shows up, but the lamp object
        doesn't).

        Args:
            location (tuple, optional): 3-tuple that defines location of Lamp.
                Defaults to ORIGIN.
            energy (float, optional): brightness or energy of Lamp. Defaults to 50.
        """
        super().__init__()
        # create an id for the lamp
        self.id = self.createID("lamp")
        strI = self.stringID(self.id)
        self.name = ["lamp" + strI]
        # create light datablock, set attributes
        lightData = D.lights.new(name=self.name[0], type="POINT")
        lightData.energy = energy
        # create new object with our light datablock
        lightObject = D.objects.new(name=self.name[0], object_data=lightData)
        # link light object
        C.collection.objects.link(lightObject)
        # make it active
        C.view_layer.objects.active = lightObject
        # change location
        lightObject.location = location
        # update scene, if needed
        dg = C.evaluated_depsgraph_get()
        dg.update()
