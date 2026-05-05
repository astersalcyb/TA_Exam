bl_info = {
    "name" : "Scene Validation Tool",
    "author" : "Aster Sala Cybulski",
    "version" : (1,0),
    "blender" : (5,0,1),
    "category" : "Object",
    
}

import bpy


class ValidateItem(bpy.types.PropertyGroup):
    # I want data storage to store results, I do this with Property Group which makes lists
    name : bpy.props.StringProperty()
    issue : bpy.props.StringProperty()



class SceneChecker(bpy.types.Operator):
    # I want to create a custom operator for this tool
    bl_idname = "scene.check_scene"
    bl_label = "Scene Checker"
    
    def execute(self, context):
        # This will run the following script when the user clicks the button
        # We want to start by looping over every object in our scene and making sure it goes only through meshes
        
        #simplify script for future use
        scene = context.scene
        #clear out previous results in list (this "validation_items" can be found during the registration part of our script)
        scene.check_items.clear()
        
        
        for obj in scene.objects:
            if obj.type != 'MESH':
                continue
            
            # Collect issues so it prints in UI all together
            issues = [] 
            
            # Check scale
            if obj.scale != (1,1,1):
                issues.append("Scale")

            # Check rotation
            if obj.rotation_euler != (0, 0, 0):
                issues.append("Rotation")

            # Check naming
            if not obj.name.startswith("SM_"):
                issues.append("Naming Convention")

            if issues:
                item = scene.check_items.add()
                item.name = obj.name
                item.issue = "Unapplied: " + ",".join(issues)
                # We combine everything into one string to simplify and make more readable


        self.report({'INFO'}, "Validation Complete")
                
            
        return {'FINISHED'}
        
        
class UI_SceneValidation(bpy.types.UIList):
    # Create a UI list to be able to visualize the data easier
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row()
        row.label(text=item.name, icon='OBJECT_DATA')
        row.label(text=item.issue)
        
    
class Display_ValidateScene(bpy.types.Panel):
    # We prepare our panel where our tool will be displayed
    bl_label = "Scene Validation"
    bl_idname = "Display_ValidateScene"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    bl_options = {'DEFAULT_CLOSED'}
    bl_category = "scene"
    bl_icon = "CHECKMARK"
    
    def draw(self, context):
        # We make out layout and we use the custom operator we've created on our previous class
        layout = self.layout
        scene = context.scene
        
        layout.operator("scene.check_scene")
        
        # Draw my UI list using the items in my validation list
        layout.template_list(
        "UI_SceneValidation",
        "", # empty for now because i dont have multiple lists
        scene,
        "check_items", # items in my validation list
        scene,
        "check_index" # index of items in my validation list
        )


# For each class we make and want to run, we must register and unregister them in this format
# We simplify this process by making a list of our classes and looping through it

classes = (
    ValidateItem,
    SceneChecker,
    UI_SceneValidation,
    Display_ValidateScene
)


def register():
    for cls in classes : 
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.check_items = bpy.props.CollectionProperty(type=ValidateItem)
    bpy.types.Scene.check_index = bpy.props.IntProperty()


def unregister():
    del bpy.types.Scene.check_items
    del bpy.types.Scene.check_index

    
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
        


if __name__ == "__main__":
    register()
    
    