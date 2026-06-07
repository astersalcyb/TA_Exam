import bpy
import os
import json
from bpy_extras.io_utils import ExportHelper

# EXPORT OPTIONS
# just like Fix_Options in validation.py, this is a container that stores all the user's export preferences on the scene

class Export_Options(bpy.types.PropertyGroup):
    # the folder the user wants to export into, subtype='DIR_PATH' tells blender to show a folder picker icon next to it 
    export_path: bpy.props.StringProperty(name="Export Path",description="Folder where FBX files and manifest.json will be saved",subtype='DIR_PATH',default="")

    # depending on which engine are we targeting, this affects FBX axis settings and the folder names we create
    engine: bpy.props.EnumProperty(
        name="Target Engine",
        items=[
            ('UE',    "Unreal Engine", "Export with Unreal Engine settings"),
            ('UNITY', "Unity",         "Export with Unity settings"),
        ],
        default='UE'
    )

    # export only what the user has selected in the viewport, or every mesh in the scene
    export_mode: bpy.props.EnumProperty(
        name="Export Mode",
        items=[
            ('SELECTED', "Selected Only", "Only export selected objects"),
            ('SCENE',    "Full Scene",    "Export every mesh in the scene"),
        ],
        default='SELECTED'
    )

    # if True, we run the scene validator before exporting and warn the user if any issues are found, we want this in case we plan to export for
    # example to unreal, but i fixed my issues with unity settings or didn't solve any of my issues
    validate_before_export: bpy.props.BoolProperty(
        name="Validate Before Export",
        description="Run scene validation before exporting and warn if issues exist",
        default=True
    )
    
    # one file per mesh is the standard for game engines, it makes reimporting individual assets much cleaner
    export_individual: bpy.props.BoolProperty(
        name="One File Per Mesh",
        description="Export each mesh as a separate FBX file",
        default=True
    )

# BUILD FOLDER STRUCTURE
# this function takes the root export path the user chose and creates the subfolder layout inside it, 
# os.makedirs with exist_ok=True means it won't crash if the folder already exists, it just moves on, so it acts as a safety meassure
# for UE we follow the standard Content Browser structure, for Unity we follow the standard Assets folder structure
# the function returns the path to the Meshes subfolder so the export functions know exactly where to put the FBX files

def build_folder_structure(export_path, engine):

    if engine == 'UE': # UNREAL ENGINE
        meshes_folder = os.path.join(export_path, "Content", "Meshes")
    else:  # UNITY
        meshes_folder = os.path.join(export_path, "Assets", "Meshes")

    os.makedirs(meshes_folder, exist_ok=True)  # create folder (and parents) if missing

    return meshes_folder  # hand back the path so the exporter knows where to write


# GET FBX SETTINGS PER ENGINE
# UE and Unity both use .fbx but they expect slightly different axis orientations, which is a very common source of errors when importing
# UE = forward -Y / up Z | Unity = forward Z / up Y

def get_fbx_settings(engine):

    # these settings are shared by both engines, they are the standard "game engine safe" FBX export options in blender
    shared = {
        "use_mesh_modifiers":   True,   # apply modifiers before exporting
        "mesh_smooth_type":     'FACE', # per-face smoothing, safest for game engines
        "use_tspace":           True,   # export tangent space for normal maps
        "add_leaf_joints":      False,  # no extra leaf bones (we only export meshes)
        "bake_space_transform": True,   # bake the axis conversion into the mesh data
        "apply_unit_scale":     True,   # make sure the scale is 1:1 in the engine
        "apply_scale_options":  'FBX_SCALE_ALL',  # apply all scale factors
        "use_selection":        True,   # we always select the object ourselves before calling
    }

    if engine == 'UE':
        shared["axis_forward"] = '-Y'
        shared["axis_up"]      = 'Z'

    else:  # UNITY
        shared["axis_forward"] = 'Z'
        shared["axis_up"]      = 'Y'

    return shared # return a dictionary of keyword arguments that will be unpacked directly into bpy.ops.export_scene.fbx()



# EXPORT A SINGLE MESH AS FBX
# this function handles the actual blender export process for one object, bpy.ops.export_scene.fbx always exports whatever is currently selected
# deselect everything /select only the object we want /make it the active object /run the export /restore the original selection afterwards
# we also build the output file path here: meshes_folder + obj.name + ".fbx" and return it so the manifest text file knows what file was created

def export_mesh_fbx(obj, meshes_folder, engine):

    # save original selection state so we can restore it later
    original_selection = [o for o in bpy.context.selected_objects]
    original_active    = bpy.context.view_layer.objects.active
    # isolate this object for export 
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # build the output file path, use obj.name as the file name
    file_name = obj.name + ".fbx"
    file_path = os.path.join(meshes_folder, file_name)

    # get the engine specific settings and run the export
    settings = get_fbx_settings(engine)
    
    with bpy.context.temp_override( # bpy.ops.export_scene.fbx requires a valid window context to run, 
    # we override the context with a real window so blender thinks it's coming from the correct place
        window=bpy.context.window_manager.windows[0]  # grab the main blender window
    ):
        bpy.ops.export_scene.fbx(filepath=file_path, **settings)

    # restore original selection
    for o in bpy.context.scene.objects:
        o.select_set(False)
    for o in original_selection:
        o.select_set(True)
    bpy.context.view_layer.objects.active = original_active

    return file_path  # hand back the path for the manifest

# MANIFEST JSON WRITER

# this function takes the list of exported mesh info we built up during the export loop and writes it to manifest.json in the root export folder, which UE/Unitity importer script will read

def write_manifest(export_path, engine, exported_meshes):

    # build the content path string depending on the engine, this is the "virtual" path inside the engine's project, not a real file system path yet
    if engine == 'UE': # UE
        content_root = "/Game/Meshes"
    else:  # UNITY
        content_root = "Assets/Meshes"

    # data structure we want to write, exported_meshes is a list of (obj_name, file_path) tuples that we collected during the export loop
    manifest = {
        "engine":      engine,
        "export_path": export_path,
        "meshes": [
            {
                "file":         os.path.basename(file_path),  # just the filename, not full path
                "asset_name":   obj_name,                     # asset name in engine same as original mesh name
                "content_path": content_root,                 # where in the engine's project it goes
                "source_path":  file_path,                    # full path for the engine script to read
            }
            for obj_name, file_path in exported_meshes  # one entry per exported mesh
        ]
    }

    # write to a file called manifest.json in the root export folder
    manifest_path = os.path.join(export_path, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=4)  # indent=4 makes it human-readable
    
    return manifest_path


# COLLECT OBJECTS TO EXPORT
# depending on the export mode chosen, we either grab selected objects or every mesh in the scene (only include MESH type objects)

def get_objects_to_export(context):

    opts = context.scene.export_options

    if opts.export_mode == 'SELECTED':
        # only meshes that are currently selected in the viewport
        objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
    else:
        # every mesh in the scene
        objects = [obj for obj in context.scene.objects if obj.type == 'MESH']

    return objects

# EXPORT OPERATOR
# operator the export button calls, ties all the helper functions together in the right order

class Export_Scene(bpy.types.Operator):
    bl_idname = "scene.export_scene"
    bl_label  = "Export Scene"

    def execute(self, context):
        scene = context.scene
        opts  = scene.export_options

        # make sure the user has chosen an export path
        export_path = bpy.path.abspath(opts.export_path) # bpy.path.abspath converts blender's relative "//" paths to real absolute paths

        if not export_path or not os.path.isdir(export_path):
            self.report({'ERROR'}, "Please set a valid export path first")
            return {'CANCELLED'}

        # optional pre-export validation
        if opts.validate_before_export: # re-run the scene checker so the results are current
            bpy.ops.scene.check_scene()

            # check if any mesh issues exist
            if len(scene.mesh_check_items) > 0: # warn but NOT cancel, user might want to export anyway, they can uncheck "Validate Before Export" if they want to skip this warning 
                self.report(
                    {'WARNING'},
                    f"{len(scene.mesh_check_items)} mesh issue(s) found. Consider fixing before export."
                )

        objects = get_objects_to_export(context)  # collect objects 

        if not objects: # safety meassure
            self.report({'WARNING'}, "No mesh objects found to export")
            return {'CANCELLED'}

        # build the folder structure
        meshes_folder = build_folder_structure(export_path, opts.engine)

        # export each object and collect results 
        exported_meshes = []  # will hold (obj_name, file_path) tuples

        for obj in objects:
            try:
                file_path = export_mesh_fbx(obj, meshes_folder, opts.engine)
                exported_meshes.append((obj.name, file_path))

            except Exception as e: # if one object fails, report it but keep going so the rest of the scene still exports
                self.report({'WARNING'}, f"Failed to export {obj.name}: {str(e)}")

        if not exported_meshes:
            self.report({'ERROR'}, "No meshes were exported successfully")
            return {'CANCELLED'}

        # write the manifest 
        manifest_path = write_manifest(export_path, opts.engine, exported_meshes)

        self.report({'INFO'},f"Exported {len(exported_meshes)} mesh(es) to {export_path}. Manifest written.")

        return {'FINISHED'}

# REGISTER/UNREGISTER

classes = (
    Export_Options,
    Export_Scene,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    # register the export options on the scene so they persist
    bpy.types.Scene.export_options = bpy.props.PointerProperty(type=Export_Options)


def unregister():
    del bpy.types.Scene.export_options

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
