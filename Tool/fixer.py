import bpy
import re # library for name splitting by it's components (ex. prefix, name, suffix...)
from . import validation
from .validation import Fix_Options, Fix_Mat_Options # import my data containers
from mathutils import Vector # for calculating pivot at bottom of mesh

# MESH FIX FUNCTIONS

def fix_transforms(obj, context, location=False, rotation=False, scale=False): # function to fix transforms (scale,location,rotation)
    
    if obj.type != 'MESH':
        return False
    
    bpy.ops.object.select_all(action='DESELECT') # deselect all
    obj.select_set(True) # select current 
    context.view_layer.objects.active = obj # make current active
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale) # apply transformations
    return True

def get_required_prefix(context):

    options = context.scene.fix_options

    if options.naming_mode == 'UE':
        return "SM_"

    elif options.naming_mode == 'UNITY':
        return "M_"

    elif options.naming_mode == 'CUSTOM':
        return options.naming_prefix

    return ""

def fix_naming(obj, context):

    prefix = get_required_prefix(context)

    if prefix == "":
        return

    name = obj.name # get mesh name

    # remove old prefix (simple safe split)
    if "_" in name:
        name = name.split("_", 1)[1]

    obj.name = prefix + name

def fix_pivot(obj, context):
    # ensure correct context
    mode = context.scene.fix_options.pivot_mode

    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj
    # store current 3D cursor position
    cursor_backup = context.scene.cursor.location.copy()
    # pivot depending on option chosen in UI
    try:
        if mode == 'ORIGIN':

            context.scene.cursor.location = (0, 0, 0)
            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

        elif mode == 'CENTER':

            bpy.ops.object.origin_set(
                type='ORIGIN_GEOMETRY',
                center='BOUNDS'
            )

        elif mode == 'BOTTOM':

            # calculate bottom center of bounding box
            world_corners = [
                obj.matrix_world @ Vector(corner)
                for corner in obj.bound_box
            ]

            min_z = min(v.z for v in world_corners)

            center_x = sum(v.x for v in world_corners) / 8
            center_y = sum(v.y for v in world_corners) / 8

            context.scene.cursor.location = (
                center_x,
                center_y,
                min_z
            )

            bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    finally:
        context.scene.cursor.location = cursor_backup

    return True

# IDS FOR ISSUES TO FIX PER MESH, TO CONNECT WITH CORRESPONDING FIX FUNCTION
FIXERS = {
    "SCALE_NOT_APPLIED":
        lambda obj, ctx: fix_transforms(obj, ctx, scale=True),

    "ROTATION_NOT_APPLIED":
        lambda obj, ctx: fix_transforms(obj, ctx, rotation=True),

    "LOCATION_NOT_APPLIED":
        lambda obj, ctx: fix_transforms(obj, ctx, location=True),

    "WRONG_NAMING_CONVENTION": fix_naming,
    "PIVOT_INVALID": fix_pivot,
}

# MATERIAL FIX FUNCTIONS

def fix_no_material(mat_item_name, context):
    """Assign a new default material to a mesh that has none."""
    obj = context.scene.objects.get(mat_item_name)
    if obj is None or obj.type != 'MESH':
        return False

    # build a sensible default material name from the mesh name
    prefix = validation.get_required_mat_prefix(context)
    # strip any existing mesh prefix and use the core name
    base = mat_item_name
    if "_" in base:
        base = base.split("_", 1)[1]
    mat_name = prefix + base if prefix else "M_" + base

    # reuse existing material with that name or create a fresh one
    mat = bpy.data.materials.get(mat_name) or bpy.data.materials.new(name=mat_name)

    if len(obj.material_slots) == 0:
        obj.data.materials.append(mat)
    else:
        obj.material_slots[0].material = mat

    return True


def fix_material_naming(mat_name, context):
    # rename a material to match the chosen naming convention
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        return False

    prefix = validation.get_required_mat_prefix(context)
    if prefix == "":
        return True

    if mat.name.startswith(prefix):
        return True  # already correct

    # strip any existing prefix up to the first underscore
    name = mat.name
    if "_" in name:
        name = name.split("_", 1)[1]

    # avoid name collisions by letting blender deduplicate
    mat.name = prefix + name
    return True


def fix_duplicate_material(mat_name, context):
    # remap all users of a duplicate material to the original and delete the duplicate
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        return False

    base_name = re.sub(r"\.\d+$", "", mat.name)
    original = bpy.data.materials.get(base_name)

    if original is None or original == mat:
        return False

    mat.user_remap(original)
    bpy.data.materials.remove(mat)
    return True


def fix_unused_material(mat_name, context):
    # remove a material that has no users
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        return False

    if mat.users == 0:
        bpy.data.materials.remove(mat)
        return True

    return False


# map issue IDs to their material fix functions
# each function receives (item.name, context)
MATERIAL_FIXERS = {
    "NO_MATERIAL_ASSIGNED": fix_no_material,
    "WRONG_MATERIAL_NAMING": fix_material_naming,
    "DUPLICATE_MATERIAL": fix_duplicate_material,
    "UNUSED_MATERIAL": fix_unused_material,
}

# MAIN FIX FUNCTIONS

def run_fixes(context, selected_only=False, allowed_issues=None):
    # loop though checked meshes
    for item in context.scene.mesh_check_items:
        if selected_only and not item.selected: # if mesh is selected
            continue

        obj = bpy.data.objects.get(item.name) # get current mesh name
        if obj is None: # safety meassure
            continue

        issues = [i.strip() for i in item.issue.split(",") if i.strip()] # make list of issues of mesh
        remaining_issues = [] # track remaining unfixed issues (for ex. if we use custom fix and don't check all boxes)

        for issue in issues:
            if allowed_issues is not None and issue not in allowed_issues: # loop through issues we want to fix
                remaining_issues.append(issue) # if the issue is not checked to fix, place it in the remainding issues list
                continue

            fixer = FIXERS.get(issue) # connect issue to fixer dictionary to get fixer function
            if fixer:
                success = fixer(obj, context) # run fixer
                if not success: # if fixer doesnt work
                    remaining_issues.append(issue) # add to remaining issues
            else:
                remaining_issues.append(issue) # same here

        item.issue = ", ".join(remaining_issues) # update issue list


def run_material_fixes(context, selected_only=False, allowed_issues=None):
    # loop through material_check_items and apply the relevant fix functions
    # we iterate over a snapshot of names because fixing (e.g. removing a duplicate) can modify bpy.data.materials while we are reading it
    items_snapshot = [(item.name, item.issue, item.selected) for item in context.scene.material_check_items]

    for name, issue_str, selected in items_snapshot:
        if selected_only and not selected:
            continue

        issues = [i.strip() for i in issue_str.split(",") if i.strip()]

        for issue in issues:
            if allowed_issues is not None and issue not in allowed_issues:
                continue

            fixer = MATERIAL_FIXERS.get(issue)
            if fixer:
                fixer(name, context)

# MESH FIX OPERATORS

class Fix_All(bpy.types.Operator):
    bl_idname = "scene.fix_all"
    bl_label = "Fix All"

    @classmethod
    def poll(cls, context): # control if button/operator is enabled
        return any(item.selected for item in context.scene.mesh_check_items) # enable fix all only if mesh selected

    def execute(self, context):

        if not any(item.selected for item in context.scene.mesh_check_items): # check if mesh selected and if not, send warning
            self.report({'WARNING'}, "No items selected")
            return {'CANCELLED'} # cancel operation

        run_fixes(context, selected_only=True) # run all available fixes
        bpy.ops.scene.check_scene() # rerun validationa afterwards

        return {'FINISHED'}  

class Fix_Custom(bpy.types.Operator):
    bl_idname = "scene.fix_custom"
    bl_label = "Fix Custom"

    @classmethod
    def poll(cls, context): # control if button/operator is enabled
        return any(item.selected for item in context.scene.mesh_check_items) # is mesh selected? 

    def execute(self, context):
        opts = context.scene.fix_options # read ui custom fix options

        allowed = set() # what fix custom options are checked? put them in this list 
        if opts.fix_scale:
            allowed.update({"SCALE_NOT_APPLIED"})
        if opts.fix_rotation:
            allowed.update({"ROTATION_NOT_APPLIED"})
        if opts.fix_location:
            allowed.update({"LOCATION_NOT_APPLIED"})
        if opts.fix_naming:
            allowed.update({"WRONG_NAMING_CONVENTION"})
        if opts.fix_pivot:
            allowed.update({"PIVOT_INVALID"})

        if not allowed: # if nothing is checked then cancell the operation
            self.report({'WARNING'}, "No fix options selected")
            return {'CANCELLED'}

        run_fixes(context, selected_only=True, allowed_issues=allowed) # run only checked fixes
        bpy.ops.scene.check_scene() # rerun validation afterwards
        return {'FINISHED'}

# MATERIAL FIX OPERATORS

class Fix_All_Materials(bpy.types.Operator):
    bl_idname = "scene.fix_all_materials"
    bl_label = "Fix All"

    @classmethod
    def poll(cls, context):
        return any(item.selected for item in context.scene.material_check_items)

    def execute(self, context):
        if not any(item.selected for item in context.scene.material_check_items):
            self.report({'WARNING'}, "No material items selected")
            return {'CANCELLED'}

        run_material_fixes(context, selected_only=True)
        bpy.ops.scene.check_scene()
        return {'FINISHED'}


class Fix_Custom_Materials(bpy.types.Operator):
    bl_idname = "scene.fix_custom_materials"
    bl_label = "Fix Custom"

    @classmethod
    def poll(cls, context):
        return any(item.selected for item in context.scene.material_check_items)

    def execute(self, context):
        opts = context.scene.fix_mat_options

        allowed = set()
        if opts.fix_no_material:
            allowed.add("NO_MATERIAL_ASSIGNED")
        if opts.fix_mat_naming:
            allowed.add("WRONG_MATERIAL_NAMING")
        if opts.fix_duplicate:
            allowed.add("DUPLICATE_MATERIAL")
        if opts.fix_unused:
            allowed.add("UNUSED_MATERIAL")

        if not allowed:
            self.report({'WARNING'}, "No material fix options selected")
            return {'CANCELLED'}

        run_material_fixes(context, selected_only=True, allowed_issues=allowed)
        bpy.ops.scene.check_scene()
        return {'FINISHED'}


# CLASSES LIST
classes = (
    Fix_All,
    Fix_Custom,
    Fix_All_Materials,
    Fix_Custom_Materials,
)

# REGISTRATION/UNREGISTRATION
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
