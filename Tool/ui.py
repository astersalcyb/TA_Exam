import bpy
from . import validation
from .validation import ISSUE_LABELS
from . import fixer
from .fixer import FIXERS

# SELECTION CLASSES
class SelectMeshes(bpy.types.Operator): # read values in my issue mesh list and select only checked ones in ui
    bl_idname = "scene.select_meshes"
    bl_label = "Selected Meshes"

    def execute(self, context):
        scene = context.scene # get current scene
        bpy.ops.object.select_all(action='DESELECT') # clear any previous selection

        for item in scene.mesh_check_items: # loop through selected meshes 
            if item.selected: # if my problem mesh is selected
                obj = scene.objects.get(item.name) # get mesh name
                if obj: # if mesh exists
                    obj.select_set(True) # set mesh as true (selected)

        return {'FINISHED'}

class DeselectMeshes(bpy.types.Operator): # deselection button for all meshes in list
    bl_idname = "scene.deselect_meshes"
    bl_label = "Deselect All"

    def execute(self, context):
        scene = context.scene

        for item in scene.mesh_check_items: # loop through selected meshes 
            item.selected = False # clear selection per mesh

        bpy.ops.object.select_all(action='DESELECT') # deselect all objs in scene
        return {'FINISHED'}

class SelectAllMeshes(bpy.types.Operator): # selection button for all meshes in list
    bl_idname = "scene.select_all_meshes"
    bl_label = "Select All"

    def execute(self, context):
        scene = context.scene

        for item in scene.mesh_check_items: # loop through selected meshes 
            item.selected = True # set as True selected per mesh

        bpy.ops.object.select_all(action='SELECT') # mark all objs in scene as selected
        return {'FINISHED'}

# VALIDATION CLASSES FOR UI

class UI_MeshValidation(bpy.types.UIList): # create custom ui list
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname): # draw methods
        row = layout.row(align=True) # horizontal row layout (with alignment to look better)
        row.prop(item, "selected", text="") # draw checkbox next to my issue mesh
        row.label(text=item.name) # issue mesh's name as string text

        issue_ids = item.issue.split(",") if item.issue else [] # make list of issues of mesh
        labels = [ISSUE_LABELS.get(i, i) for i in issue_ids] # convert issue id's to labels
        row.label(text=", ".join(labels)) # issue text from labels


class UI_MaterialValidation(bpy.types.UIList): # create custom ui list
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname): # draw methods
        row = layout.row(align=True) # horizontal row layout (with alignment to look better)
        row.label(text=item.name, icon='MATERIAL') # material name with icon 

        issue_ids = item.issue.split(",") if item.issue else []  # make list of issues of material
        labels = [ISSUE_LABELS.get(i, i) for i in issue_ids] # convert issue id's to labels
        row.label(text=", ".join(labels))  # issue text from labels

# UI DISPLAY
class Display_ValidateScene(bpy.types.Panel):
    bl_label = "Scene Validation"
    bl_idname = "DISPLAY_PT_validate_scene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        # VALIDATION TOOL TITLE
        layout.operator("scene.check_scene")
        # MESH ISSUE UI WITH LIST
        layout.label(text="Mesh Issues", icon='OBJECT_DATA')
        layout.template_list(
            "UI_MeshValidation",
            "",
            scene,
            "mesh_check_items",
            scene,
            "mesh_check_index"
        )
        # SELECT ALL/DESELECT ALL BUTTONS
        row = layout.row(align=True)
        row.operator("scene.select_all_meshes")
        row.operator("scene.deselect_meshes")
        layout.separator()
        # MATERIAL ISSUE UI WITH LIST
        layout.label(text="Material Issues", icon='MATERIAL')
        layout.template_list(
            "UI_MaterialValidation",
            "",
            scene,
            "material_check_items",
            scene,
            "material_check_index"
        )        
        # FIXER TOOL TITLE        
        layout.separator()
        layout.label(text="Mesh Fixer", icon='MODIFIER_ON')
        # FIX ALL/FIX CUSTOM BUTTONS
        row = layout.row(align=True)
        row.operator("scene.fix_all")
        row.operator("scene.fix_custom")
        # CHECK BOXES FOR CUSTOM FIX
        box = layout.box()
        box.label(text="Custom Fix Options")
        box.prop(context.scene.fix_options, "fix_scale")
        box.prop(context.scene.fix_options, "fix_rotation")
        box.prop(context.scene.fix_options, "fix_location")
        box.prop(context.scene.fix_options, "fix_naming")
        if context.scene.fix_options.fix_naming:
            box.prop(context.scene.fix_options, "naming_mode") # show naming options
            if context.scene.fix_options.naming_mode == 'CUSTOM': # if i want custom naming prefix
                box.prop(context.scene.fix_options, "naming_prefix") # type what i want
        
        box.prop(context.scene.fix_options, "fix_pivot")
        if context.scene.fix_options.fix_pivot:
            box.prop(context.scene.fix_options, "pivot_mode") # display pivot pt options if fix pivot checked

# LIST OF ALL CLASSES USED IN FILE
classes = (
    SelectMeshes,
    DeselectMeshes,
    SelectAllMeshes,
    UI_MeshValidation,
    UI_MaterialValidation,
    Display_ValidateScene,
)
# REGISTRATION/UNREGISTRATION
def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)