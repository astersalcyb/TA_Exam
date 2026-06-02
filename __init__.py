bl_info = {
    "name": "Scene Validation Tool",
    "author": "Aster Sala Cybulski",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "category": "Object",
}

import bpy

from . import validation
from . import ui

modules = (validation, ui)

def register():
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()

if __name__ == "__main__":
    register()