bl_info = {
    "name" : "Scene Validation Tool",
    "author" : "Aster Sala Cybulski",
    "version" : (1,0),
    "blender" : (5,0,1),
    "category" : "Object",
    
}

import bpy

# DATA LISTS:

    # MESHES
class ValidateMesh(bpy.types.PropertyGroup):
    # I want data storage to store results, I do this with Property Group which makes lists
    # I will create "check_" to check items to validate if they are correct
    name : bpy.props.StringProperty()
    issue : bpy.props.StringProperty()
    # i want to make a check box for selected items in my ui list
    selected: bpy.props.BoolProperty()

    # MATERIALS
class ValidateMaterial(bpy.types.PropertyGroup):
    # Store material info in lists same as with the mesh info above
    name: bpy.props.StringProperty()
    issue: bpy.props.StringProperty()


# MESH SELECTION IN UI AND VIEWPORT

def update_mesh_selection(self, context):       
        # i want to make a funtion to select the mesh with issues in my ui and also in my viewport       
        scene = context.scene

        if not scene.mesh_check_items: # make sure my list isnt empty
            return

        index = scene.mesh_check_index # get my row index

        if index >= len(scene.mesh_check_items): # make sure index is in range of the items list index amount
            return

        item = scene.mesh_check_items[index] # get the selected mesh from my list

        obj = scene.objects.get(item.name) # find the mesh inside my scene now

        if obj:
            bpy.ops.object.select_all(action='DESELECT')

            obj.select_set(True) # select my mesh

            context.view_layer.objects.active = obj # make the selected mesh active in my viewport
            
# SELECTION/DESELECTION FOR UI
            
class SelectMeshes(bpy.types.Operator):

    bl_idname = "scene.select_meshes"

    bl_label = "Show Selected"

    def execute(self, context):

        scene = context.scene

        bpy.ops.object.select_all(action='DESELECT') # Make sure selection starts empty

        selected_objects = [] # list of selected meshes

        for item in scene.mesh_check_items: # in our list of meshes with issues

            if item.selected:

                obj = scene.objects.get(item.name) # get name of selected mesh

                if obj:
                    obj.select_set(True) # if selected mesh exists, selection set to true

                    selected_objects.append(obj) # add to selected meshes list

        # Make first selected object active
        if selected_objects:
            context.view_layer.objects.active = selected_objects[0]

        return {'FINISHED'}

class DeselectMeshes(bpy.types.Operator):
    # same as select meshes but to deselect them all in case theres a large amount of meshes with issues
    bl_idname = "scene.deselect_meshes"

    bl_label = "Deselect All"

    def execute(self, context):

        scene = context.scene

        # Remove check from all UI checkboxes
        for item in scene.mesh_check_items:
            item.selected = False # mesh selection is now false

        # Deselect objects in viewport
        bpy.ops.object.select_all(action='DESELECT')

        return {'FINISHED'}

class SelectAllMeshes(bpy.types.Operator):
    # finally this option to be able to select all meshes with issues from my ui list
    bl_idname = "scene.select_all_meshes"

    bl_label = "Select All"

    def execute(self, context):

        scene = context.scene

        # Add check to all UI checkboxes
        for item in scene.mesh_check_items:
            item.selected = True # mesh selection is now true for all

        # Select all objects in viewport
        bpy.ops.object.select_all(action='SELECT')

        return {'FINISHED'}


# WORKER CODE:

class SceneChecker(bpy.types.Operator):
    # I want to create a custom operator for this tool
    bl_idname = "scene.check_scene"
    bl_label = "Scene Checker"
    
    def execute(self, context):
        # This will run the following script when the user clicks the button
        # We want to start by looping over every object in our scene and making sure it goes only through meshes
        
        #simplify script for future use
        scene = context.scene
        
        #clear out previous results in list (this "_check_items" can be found during the registration part of our script)
        scene.mesh_check_items.clear()
        scene.material_check_items.clear()
        
        # MESHES
        
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
                
            # Check pivot pt location
            if obj.location.length != 0: # if length of my obj pivot location to origin is not 0, issue!
                pivot = obj.matrix_world.translation # detect where pivot pt is
                pivot_location = (round(pivot.x, 2), round(pivot.y, 2), round(pivot.z, 2)) # get the location but round the results
                issues.append(f"Pivot != Origin | Aprox location {pivot_location}") # pivot issue with aprox location of it

            if issues:
                item = scene.mesh_check_items.add()
                item.name = obj.name
                item.issue = "Unapplied: " + ",".join(issues)
                # We combine everything into one string to simplify and make more readable
               
        # MATERIALS               
                
        base_materials = {}
        
            # GROUPING MATERIALS
        
        for mat in bpy.data.materials: # loop through materials in my scene
            base = mat.name.split(".")[0] # just the base name of the mat

            if base not in base_materials: # if this mat doesn't have a list, create it
                base_materials[base] = []
            
            base_materials[base].append(mat)

            # PROCESS MATERIAL ISSUES
            
            for base, mats in base_materials.items():
                
                # sort materials to have original as first one, we sort by name
                mats_sorted = sorted(mats, key=lambda m: m.name)
                
                for i, mat in enumerate(mats_sorted): # enumerates and the first will be the original
                    issues = []
                    
                    if i > 0: # i dont want the original (which is the first) so i skip it
                        issues.append("Duplicate")
                        
                    if mat.users == 0: # by users it means if its used in any item in our scene
                        issues.append("Unused")
                        
                    if issues: # only if material has issues add it to the list
                        item = scene.material_check_items.add()
                        item.name = mat.name
                        item.issue = ",".join(issues) 


        self.report({'INFO'}, "Validation Complete")
                
            
        return {'FINISHED'}
        
# UI 
        
class UI_MeshValidation(bpy.types.UIList):
    # Create a UI list to be able to visualize the data easier
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row()
        row.prop(item, "selected", text="") # show check box for selected item
        row.label(text=item.name)
        row.label(text=item.issue)         
        
class UI_MaterialValidation(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        row = layout.row()
        row.label(text=item.name, icon='MATERIAL')
        row.label(text=item.issue)
              
        
# DISPLAY
        
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
        
        # MESH ISSUES
        
        # Draw my UI list using the items in my validation list
        layout.label(text="Mesh Issues", icon='OBJECT_DATA')
        layout.template_list(
        "UI_MeshValidation",
        "", # empty for now because i dont have multiple lists
        scene,
        "mesh_check_items", # items in my validation list
        scene,
        "mesh_check_index" # index of items in my validation list
        )
        
        row = layout.row()
        row.operator("scene.select_all_meshes") # display in ui select all button for ui and viewport
        row.operator("scene.select_meshes") # display in ui select in viewport button
        row.operator("scene.deselect_meshes") # display in ui deselect button for ui and viewport      
    
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


# REGISTER/UNREGISTER

    # For each class we make and want to run, we must register and unregister them in this format
    # We simplify this process by making a list of our classes and looping through it

classes = (
    ValidateMesh,
    ValidateMaterial,
    SelectMeshes,
    DeselectMeshes,
    SelectAllMeshes,
    SceneChecker,
    UI_MeshValidation,
    UI_MaterialValidation,
    Display_ValidateScene
)


def register():
    for cls in classes : 
        bpy.utils.register_class(cls)
        
    bpy.types.Scene.mesh_check_items = bpy.props.CollectionProperty(type=ValidateMesh)
    bpy.types.Scene.mesh_check_index = bpy.props.IntProperty(update=update_mesh_selection) # this allows for selecting multiple meshes in my ui list
    
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
    
    