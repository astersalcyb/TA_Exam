bl_info = {
    "name" : "Scene Validation Tool",
    "author" : "Aster Sala Cybulski",
    "version" : (1,0),
    "blender" : (5,0,1),
    "category" : "Object",
    
}

import bpy

#class ValidateScene(bpy.types.Operator):    
    
class Display_ValidateScene(bpy.types.Panel):
    # We prepare our panel where our tool will be displayed
    bl_label = "Scene Validation"
    bl_idname = "Display_ValidateScene"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "SceneValidation"
    
    def draw(self, context):
        # We make out layout and we use the custom operator we've created on our previous class
        layout = self.layout
        #layout.operator("scene.validate_scene")



# For each class we make and want to run, we must register and unregister them in this format
        
def register():
    #bpy.utils.register_class(ValidateScene)
    bpy.utils.register_class(Display_ValidateScene)

def unregister():
    #bpy.utils.unregister_class(ValidateScene)
    bpy.utils.unregister_class(Display_ValidateScene)

if __name__ == "__main__":
    register()
    
    