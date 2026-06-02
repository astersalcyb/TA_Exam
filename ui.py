import bpy
from .validation import ISSUE_LABELS


class SelectMeshes(bpy.types.Operator):
    bl_idname = "scene.select_meshes"
    bl_label = "Show Selected"

    def execute(self, context):
        scene = context.scene
        bpy.ops.object.select_all(action='DESELECT')

        selected_objects = []

        for item in scene.mesh_check_items:
            if item.selected:
                obj = scene.objects.get(item.name)
                if obj:
                    obj.select_set(True)
                    selected_objects.append(obj)

        if selected_objects:
            context.view_layer.objects.active = selected_objects[0]

        return {'FINISHED'}


class DeselectMeshes(bpy.types.Operator):
    bl_idname = "scene.deselect_meshes"
    bl_label = "Deselect All"

    def execute(self, context):
        scene = context.scene

        for item in scene.mesh_check_items:
            item.selected = False

        bpy.ops.object.select_all(action='DESELECT')
        return {'FINISHED'}


class SelectAllMeshes(bpy.types.Operator):
    bl_idname = "scene.select_all_meshes"
    bl_label = "Select All"

    def execute(self, context):
        scene = context.scene

        for item in scene.mesh_check_items:
            item.selected = True

        bpy.ops.object.select_all(action='SELECT')
        return {'FINISHED'}


class UI_MeshValidation(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.prop(item, "selected", text="")
        row.label(text=item.name)

        issue_ids = item.issue.split(",") if item.issue else []
        labels = [ISSUE_LABELS.get(i, i) for i in issue_ids]
        row.label(text=", ".join(labels))


class UI_MaterialValidation(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row(align=True)
        row.label(text=item.name, icon='MATERIAL')

        issue_ids = item.issue.split(",") if item.issue else []
        labels = [ISSUE_LABELS.get(i, i) for i in issue_ids]
        row.label(text=", ".join(labels))


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

        layout.operator("scene.check_scene")

        layout.label(text="Mesh Issues", icon='OBJECT_DATA')
        layout.template_list(
            "UI_MeshValidation",
            "",
            scene,
            "mesh_check_items",
            scene,
            "mesh_check_index"
        )

        row = layout.row(align=True)
        row.operator("scene.select_all_meshes")
        row.operator("scene.select_meshes")
        row.operator("scene.deselect_meshes")

        layout.separator()

        layout.label(text="Material Issues", icon='MATERIAL')
        layout.template_list(
            "UI_MaterialValidation",
            "",
            scene,
            "material_check_items",
            scene,
            "material_check_index"
        )


classes = (
    SelectMeshes,
    DeselectMeshes,
    SelectAllMeshes,
    UI_MeshValidation,
    UI_MaterialValidation,
    Display_ValidateScene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)