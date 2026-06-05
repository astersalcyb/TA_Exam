import bpy
import re # library for name splitting by it's components (ex. prefix, name, suffix...)
from . import validation
from .validation import Fix_Options # import my data container for my "fix custom"

# FIX FUNCTIONS
def fix_transforms(obj, context, location=False, rotation=False, scale=False): # function to fix transforms (scale,location,rotation)
    
    if obj.type != 'MESH':
        return False
    
    bpy.ops.object.select_all(action='DESELECT') # deselect all
    obj.select_set(True) # select current 
    context.view_layer.objects.active = obj # make current active
    bpy.ops.object.transform_apply(location=location, rotation=rotation, scale=scale) # apply transformations
    return True

def fix_naming(obj, context):
    
    if obj.type != 'MESH':
        return False
    
    name = obj.name # get mesh name

    # detect mesh suffixes by components (name, number)
    match = re.match(r"(.+)\.(\d+)$", name)

    if match:
        base = match.group(1) # base name
        num = match.group(2) # mesh number (in case of multiple)
        obj.name = f"SM_{base}_{num}"
    else:
        obj.name = f"SM_{name}" # if no number, just keep as SM_name

    return True

def fix_pivot(obj, context):

    # ensure correct context
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    context.view_layer.objects.active = obj

    # store current 3D cursor position
    cursor_backup = context.scene.cursor.location.copy()

    try:
        # move cursor to origin
        context.scene.cursor.location = (0, 0, 0)

        # set origin
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    finally:
        # ALWAYS restore cursor (even if operator fails)
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
    "PIVOT_NOT_ORIGIN": fix_pivot,
}

# MAIN FIX FUNCTION 
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
            allowed.update({"PIVOT_NOT_ORIGIN"})

        if not allowed: # if nothing is checked then cancell the operation
            self.report({'WARNING'}, "No fix options selected")
            return {'CANCELLED'}

        run_fixes(context, selected_only=True, allowed_issues=allowed) # run only checked fixes
        bpy.ops.scene.check_scene() # rerun validation afterwards
        return {'FINISHED'}

# CLASSES LISST
classes = (
    Fix_All,
    Fix_Custom,
)

# REGSITRATION/UNREGISTRATIO
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)