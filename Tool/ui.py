import bpy
from . import validation
from .validation import ISSUE_LABELS
from . import fixer
from .fixer import FIXERS

# MESH SELECTION OPERATORS

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

# MATERIAL SELECTION OPERATORS

class SelectAllMaterials(bpy.types.Operator):
    bl_idname = "scene.select_all_materials"
    bl_label = "Select All"

    def execute(self, context):
        for item in context.scene.material_check_items:
            item.selected = True
        return {'FINISHED'}
    
class DeselectMaterials(bpy.types.Operator):
    bl_idname = "scene.deselect_materials"
    bl_label = "Deselect All"

    def execute(self, context):
        for item in context.scene.material_check_items:
            item.selected = False
        return {'FINISHED'}

# UI LISTS

class UI_MeshValidation(bpy.types.UIList): # create custom ui list
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname): # draw methods
        row = layout.row(align=True) # horizontal row layout (with alignment to look better)
        row.prop(item, "selected", text="") # draw checkbox next to my issue mesh
        row.label(text=item.name) # issue mesh's name as string text

        issue_ids = item.issue.split(",") if item.issue else [] # make list of issues of mesh
        labels = [ISSUE_LABELS.get(i.strip(), i.strip()) for i in issue_ids] # convert issue id's to labels
        row.label(text=", ".join(labels)) # issue text from labels


class UI_MaterialValidation(bpy.types.UIList): # create custom ui list
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname): # draw methods
        row = layout.row(align=True)
        row.prop(item, "selected", text="")

        # for icons, meshes that have no material use OBJECT_DATA, materials use MATERIAL
        issue_ids = [i.strip() for i in item.issue.split(",") if i.strip()]
        if issue_ids == ["NO_MATERIAL_ASSIGNED"]:
            row.label(text=item.name, icon='OBJECT_DATA')  # item.name is the mesh name here
        else:
            row.label(text=item.name, icon='MATERIAL')

        labels = [ISSUE_LABELS.get(i, i) for i in issue_ids]
        row.label(text=", ".join(labels))

# MAIN PANEL

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
        # scan button
        layout.operator("scene.check_scene")

        # MESH ISSUES
        layout.label(text="Mesh Issues", icon='OBJECT_DATA')
        layout.template_list(
            "UI_MeshValidation",
            "",
            scene,
            "mesh_check_items",
            scene,
            "mesh_check_index"
        )
        # SELECT/DESELECT BUTTONS
        row = layout.row(align=True)
        row.operator("scene.select_all_meshes")
        row.operator("scene.deselect_meshes")

        layout.separator()

        # MESH FIXER
        layout.label(text="Mesh Fixer", icon='MODIFIER_ON')
        row = layout.row(align=True)
        row.operator("scene.fix_all")
        row.operator("scene.fix_custom")

        box = layout.box()
        box.label(text="Custom Fix Options")
        box.prop(scene.fix_options, "fix_scale")
        box.prop(scene.fix_options, "fix_rotation")
        box.prop(scene.fix_options, "fix_location")
        box.prop(scene.fix_options, "fix_naming")
        if scene.fix_options.fix_naming:
            box.prop(scene.fix_options, "naming_mode")
            if scene.fix_options.naming_mode == 'CUSTOM':
                box.prop(scene.fix_options, "naming_prefix")
        box.prop(scene.fix_options, "fix_pivot")
        if scene.fix_options.fix_pivot:
            box.prop(scene.fix_options, "pivot_mode")

        layout.separator()

        # MATERIAL ISSUES

        layout.label(text="Material Issues", icon='MATERIAL')
        layout.template_list(
            "UI_MaterialValidation",
            "",
            scene,
            "material_check_items",
            scene,
            "material_check_index"
        )
        # SELECT/DESELECT BUTTONS (mirrors the mesh section)
        row = layout.row(align=True)
        row.operator("scene.select_all_materials")
        row.operator("scene.deselect_materials")

        layout.separator()

        # MATERIAL FIXER
        layout.label(text="Material Fixer", icon='BRUSH_DATA')
        row = layout.row(align=True)
        row.operator("scene.fix_all_materials")
        row.operator("scene.fix_custom_materials")

        box = layout.box()
        box.label(text="Custom Fix Options")
        box.prop(scene.fix_mat_options, "fix_no_material")
        box.prop(scene.fix_mat_options, "fix_mat_naming")
        if scene.fix_mat_options.fix_mat_naming:
            box.prop(scene.fix_mat_options, "mat_naming_mode")
            if scene.fix_mat_options.mat_naming_mode == 'CUSTOM':
                box.prop(scene.fix_mat_options, "mat_naming_prefix")
        box.prop(scene.fix_mat_options, "fix_duplicate")
        box.prop(scene.fix_mat_options, "fix_unused")

# LIST OF ALL CLASSES USED IN FILE
classes = (
    SelectMeshes,
    DeselectMeshes,
    SelectAllMeshes,
    SelectAllMaterials,
    DeselectMaterials,
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