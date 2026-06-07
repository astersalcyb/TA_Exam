bl_info = { # info of tool
    "name": "Scene Validation Tool",
    "author": "Aster Sala Cybulski",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "category": "Object",
}

# IMPORTS + SCRIPTS IMPORT
import bpy
from . import validation
from . import ui
from . import fixer
from . import exporter

# SCRIPTS FOR TOOL LIST
modules = (validation, ui, fixer, exporter)

# REGISTRATION/UNREGISTRATION
def register():
    for module in modules:
        module.register()

def unregister():
    for module in reversed(modules):
        module.unregister()

# RUN TOOL
if __name__ == "__main__":
    register()