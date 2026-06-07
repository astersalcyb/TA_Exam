import bpy
import re

# IDs FOR FUTURE PROBLEM SOLVING
class Fix_Options(bpy.types.PropertyGroup): # container of custom fixing options 
    # all are set to true by default 
    fix_scale: bpy.props.BoolProperty(name="Scale", default=True)
    fix_rotation: bpy.props.BoolProperty(name="Rotation", default=True)
    fix_location: bpy.props.BoolProperty(name="Location", default=True)
    fix_naming: bpy.props.BoolProperty(name="Naming Convention", default=True)
    
    naming_mode: bpy.props.EnumProperty(
        name="Naming Standard",
        items=[
            ('UE', "Unreal Engine", ""),
            ('UNITY', "Unity", ""),
            ('CUSTOM', "Custom", "")
        ],
        default='UE'
    )
    
    naming_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        default="SM_"
    )
    
    fix_pivot: bpy.props.BoolProperty(name="Pivot", default=True)
    
    pivot_mode: bpy.props.EnumProperty( # pivot point options
        name="Pivot Position",
        items=[
            ('ORIGIN', "World Origin", ""),
            ('CENTER', "Object Center", ""),
            ('BOTTOM', "Bottom Of Mesh", ""),
        ],
        default='ORIGIN'
        )


class Fix_Mat_Options(bpy.types.PropertyGroup): # container of custom material fixing options
    fix_no_material: bpy.props.BoolProperty(name="No Material", default=True)
    fix_mat_naming: bpy.props.BoolProperty(name="Naming Convention", default=True)
    fix_duplicate: bpy.props.BoolProperty(name="Duplicates", default=True)
    fix_unused: bpy.props.BoolProperty(name="Unused", default=True)

    mat_naming_mode: bpy.props.EnumProperty(
        name="Naming Standard",
        items=[
            ('UE', "Unreal Engine (M_)", ""),
            ('UNITY', "Unity (mat_)", ""),
            ('CUSTOM', "Custom", ""),
        ],
        default='UE'
    )

    mat_naming_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        default="M_"
    )


ISSUE_LABELS = {  # we want to have these IDs to identify our issues easier when it comes to the second part of our tool, the fixer.
    # MESHES
    "SCALE_NOT_APPLIED": "Scale",
    "ROTATION_NOT_APPLIED": "Rotation",
    "LOCATION_NOT_APPLIED": "Location",
    "WRONG_NAMING_CONVENTION": "Naming Convention != Standard",
    "PIVOT_INVALID": "Pivot Invalid",
    # MATERIALS
    "NO_MATERIAL_ASSIGNED": "No Material",
    "WRONG_MATERIAL_NAMING": "Naming != Standard",
    "DUPLICATE_MATERIAL": "Duplicate",
    "UNUSED_MATERIAL": "Unused",
}

# UPDATE FUNCTIONS
#MESH
def update_mesh_checkbox(self, context): # to update everytime we check something on/off from our issue mesh list
    scene = context.scene
    obj = scene.objects.get(self.name)

    if not obj: # safety meassure
        return

    if self.selected: # if mesh is selected in checkbox
        obj.select_set(True) # mesh selected
        context.view_layer.objects.active = obj # make mesh active
    else:
        obj.select_set(False)
#MATERIAL
def update_material_checkbox(self, context):
    # Materials cannot be "selected" in the viewport like meshes,
    # but we store the flag for use by fix operators.
    # No extra action needed here — the BoolProperty stores the value automatically.
    pass

# DATA LISTS:

# MESHES
class ValidateMesh(bpy.types.PropertyGroup):
    # I want data storage to store results, I do this with Property Group which makes lists
    # I will create "check_" to check items to validate if they are correct
    name: bpy.props.StringProperty()
    issue: bpy.props.StringProperty()
    # i want to make a check box for selected items in my ui list
    selected: bpy.props.BoolProperty(update=update_mesh_checkbox)


class ValidateMaterial(bpy.types.PropertyGroup):
    # Store material/mesh info for material issues
    # For NO_MATERIAL_ASSIGNED the name is the mesh name
    # For all other issues the name is the material name
    name: bpy.props.StringProperty()
    issue: bpy.props.StringProperty()
    selected: bpy.props.BoolProperty(update=update_material_checkbox)

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

            issues = []

            # Location check (from helper logic)
            loc_ok = all(abs(v) < 1e-6 for v in obj.location) # this method seems to be more precise to determine location or other transform options
            if not loc_ok:
                issues.append("LOCATION_NOT_APPLIED")

            # Scale check
            scale_ok = all(abs(v - 1.0) < 1e-6 for v in obj.scale)
            if not scale_ok:
                issues.append("SCALE_NOT_APPLIED")

            # Rotation check
            if obj.rotation_mode == 'QUATERNION': # check quaternion rotations
                q = obj.rotation_quaternion
                rot_ok = (
                    abs(q.w - 1.0) < 1e-6 and
                    abs(q.x) < 1e-6 and
                    abs(q.y) < 1e-6 and
                    abs(q.z) < 1e-6
                )

            elif obj.rotation_mode == 'AXIS_ANGLE': # check axis angular rotations
                angle = obj.rotation_axis_angle[0]
                rot_ok = abs(angle) < 1e-6

            else:
                rot_ok = all(abs(v) < 1e-6 for v in obj.rotation_euler) # check euler rotation

            if not rot_ok:
                issues.append("ROTATION_NOT_APPLIED") 

            # --- NAMING CHECK ---
            if not validate_naming(obj, context):
                issues.append("WRONG_NAMING_CONVENTION")

            # --- PIVOT CHECK ---
            if obj.location.length != 0: # If pivot not at origin
                pivot = obj.matrix_world.translation # world space position
                pivot_location = (pivot.x, pivot.y, pivot.z)  # kept for future use
                issues.append("PIVOT_INVALID")

            # store results
            if issues:
                item = scene.mesh_check_items.add()
                item.name = obj.name
                item.issue = ",".join(issues)
                
        # MATERIALS

        # flag meshes that have no material assigned
        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            has_material = any(slot.material for slot in obj.material_slots)
            if not has_material:
                item = scene.material_check_items.add()
                item.name = obj.name          # key = mesh name so fixer can find the object
                item.issue = "NO_MATERIAL_ASSIGNED"

        # per material in bpy.data.materials -> duplicates, unused, wrong naming
        base_materials = {}

        for mat in bpy.data.materials:  # loop through materials in my scene
            base = re.sub(r"\.\d+$", "", mat.name)  # strip suffixes

            if base not in base_materials:
                base_materials[base] = []

            base_materials[base].append(mat)

        for base, mats in base_materials.items():

            # sort so the "original" (no numeric suffix) comes first
            mats_sorted = sorted(mats, key=lambda m: m.name)

            for i, mat in enumerate(mats_sorted):
                issues = []

                if i > 0: # anything after the first is a duplicate
                    issues.append("DUPLICATE_MATERIAL")

                if mat.users == 0:
                    issues.append("UNUSED_MATERIAL")

                if not validate_material_naming(mat, context):
                    issues.append("WRONG_MATERIAL_NAMING")

                if issues:
                    item = scene.material_check_items.add()
                    item.name = mat.name
                    item.issue = ",".join(issues)

        self.report({'INFO'}, "Validation Complete")

        return {'FINISHED'}

# FUNCTION FOR NAMING CONVENTIONS
# MESH
def get_required_prefix(context):

    options = context.scene.fix_options
    # different naming mode and what prefix it gives
    if options.naming_mode == 'UE':
        return "SM_"

    elif options.naming_mode == 'UNITY':
        return "M_"

    elif options.naming_mode == 'CUSTOM':
        return options.naming_prefix # chose what naming prefix i want

    return ""

def validate_naming(obj, context):

    prefix = get_required_prefix(context)

    if prefix == "":
        return True

    return obj.name.startswith(prefix)

# MATERIAL
def get_required_mat_prefix(context):
    options = context.scene.fix_mat_options

    if options.mat_naming_mode == 'UE':
        return "M_"
    elif options.mat_naming_mode == 'UNITY':
        return "mat_"
    elif options.mat_naming_mode == 'CUSTOM':
        return options.mat_naming_prefix
    return ""

def validate_material_naming(mat, context):
    prefix = get_required_mat_prefix(context)
    if prefix == "":
        return True
    return mat.name.startswith(prefix)

# REGISTER/UNREGISTER

# For each class we make and want to run, we must register and unregister them in this format
# We simplify this process by making a list of our classes and looping through it

classes = (
    Fix_Options,
    Fix_Mat_Options,
    ValidateMesh,
    ValidateMaterial,
    SceneChecker,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    # we have to individually register these because they store information for multiple items instead of it just being a function used once (if that makes sense)
    bpy.types.Scene.mesh_check_items = bpy.props.CollectionProperty(type=ValidateMesh)
    bpy.types.Scene.mesh_check_index = bpy.props.IntProperty()

    bpy.types.Scene.material_check_items = bpy.props.CollectionProperty(type=ValidateMaterial)
    bpy.types.Scene.material_check_index = bpy.props.IntProperty()

    bpy.types.Scene.fix_options = bpy.props.PointerProperty(type=Fix_Options)
    bpy.types.Scene.fix_mat_options = bpy.props.PointerProperty(type=Fix_Mat_Options)


def unregister():
    del bpy.types.Scene.mesh_check_items
    del bpy.types.Scene.mesh_check_index

    del bpy.types.Scene.material_check_items
    del bpy.types.Scene.material_check_index

    del bpy.types.Scene.fix_options
    del bpy.types.Scene.fix_mat_options

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
