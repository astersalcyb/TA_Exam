bl_info = {
    "name": "Scene Validation Tool",
    "author": "Aster Sala Cybulski",
    "version": (1, 0),
    "blender": (5, 0, 1),
    "category": "Object",

}

import bpy


# DATA LISTS:

# MESHES
class ValidateMesh(bpy.types.PropertyGroup):
    # I want data storage to store results, I do this with Property Group which makes lists
    # I will create "check_" to check items to validate if they are correct
    name: bpy.props.StringProperty()
    issue: bpy.props.StringProperty()
    # i want to make a check box for selected items in my ui list
    selected: bpy.props.BoolProperty()

    # MATERIALS


class ValidateMaterial(bpy.types.PropertyGroup):
    # Store material info in lists same as with the mesh info above
    name: bpy.props.StringProperty()
    issue: bpy.props.StringProperty()


# IDs FOR FUTURE PROBLEM SOLVING

ISSUE_LABELS = {
    # we want to have these IDs to identify our issues easier when it comes to the second part of our tool, the fixer.

    # MESHES
    "SCALE_NOT_APPLIED": "Scale",
    "ROTATION_NOT_APPLIED": "Rotation",
    "WRONG_NAMING_CONVENTION": "Naming Convention",
    "PIVOT_NOT_ORIGIN": "Pivot != Origin",

    # MATERIALS
    "DUPLICATE_MATERIAL": "Duplicate",
    "UNUSED_MATERIAL": "Unused",
}

# WORKER CODE:

class SceneChecker(bpy.types.Operator):
    # I want to create a custom operator for this tool
    bl_idname = "scene.check_scene"
    bl_label = "Scene Checker"

    def execute(self, context):
        # This will run the following script when the user clicks the button
        # We want to start by looping over every object in our scene and making sure it goes only through meshes

        # simplify script for future use
        scene = context.scene

        # clear out previous results in list (this "_check_items" can be found during the registration part of our script)
        scene.mesh_check_items.clear()
        scene.material_check_items.clear()

        # MESHES

        for obj in scene.objects:
            if obj.type != 'MESH':
                continue

            # Collect issues so it prints in UI all together
            issues = []

            # Check scale
            if obj.scale != (1, 1, 1):
                issues.append("SCALE_NOT_APPLIED")

            # Check rotation
            if obj.rotation_euler != (0, 0, 0):
                issues.append("ROTATION_NOT_APPLIED")

            # Check naming
            if not obj.name.startswith("SM_"):
                issues.append("WRONG_NAMING_CONVENTION")

            # Check pivot pt location
            if obj.location.length != 0:  # if length of my obj pivot location to origin is not 0, issue!
                pivot = obj.matrix_world.translation  # detect where pivot pt is
                pivot_location = (pivot.x, pivot.y, pivot.z)  # store pivot pt location, i might want to use this later
                issues.append(f"PIVOT_NOT_ORIGIN")  # pivot issue

            if issues:
                item = scene.mesh_check_items.add()
                item.name = obj.name
                item.issue = ",".join(issues)
                # We combine everything into one string to simplify and make more readable

        # MATERIALS

        base_materials = {}

        # GROUPING MATERIALS

        for mat in bpy.data.materials:  # loop through materials in my scene
            base = mat.name.split(".")[0]  # just the base name of the mat

            if base not in base_materials:  # if this mat doesn't have a list, create it
                base_materials[base] = []

            base_materials[base].append(mat)

            # PROCESS MATERIAL ISSUES

            for base, mats in base_materials.items():

                # sort materials to have original as first one, we sort by name
                mats_sorted = sorted(mats, key=lambda m: m.name)

                for i, mat in enumerate(mats_sorted):  # enumerates and the first will be the original
                    issues = []

                    if i > 0:  # i dont want the original (which is the first) so i skip it
                        issues.append("DUPLICATE_MATERIAL")

                    if mat.users == 0:  # by users it means if its used in any item in our scene
                        issues.append("UNUSED_MATERIAL")

                    if issues:  # only if material has issues add it to the list
                        item = scene.material_check_items.add()
                        item.name = mat.name
                        item.issue = ",".join(issues)

        self.report({'INFO'}, "Validation Complete")

        return {'FINISHED'}


# REGISTER/UNREGISTER

# For each class we make and want to run, we must register and unregister them in this format
# We simplify this process by making a list of our classes and looping through it

classes = (
    ValidateMesh,
    ValidateMaterial,
    SceneChecker,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.mesh_check_items = bpy.props.CollectionProperty(type=ValidateMesh)
    bpy.types.Scene.mesh_check_index = bpy.props.IntProperty(
        update=update_mesh_selection)  # this allows for selecting multiple meshes in my ui list

    bpy.types.Scene.material_check_items = bpy.props.CollectionProperty(type=ValidateMaterial)
    bpy.types.Scene.material_check_index = bpy.props.IntProperty()


def unregister():
    del bpy.types.Scene.mesh_check_items
    del bpy.types.Scene.mesh_check_index

    del bpy.types.Scene.material_check_items
    del bpy.types.Scene.material_check_index

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()