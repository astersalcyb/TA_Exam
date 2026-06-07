import bpy
import os
import json

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

# BUILD FOLDER STRUCTURE
# this function takes the root export path the user chose and creates the subfolder layout inside it, 
# os.makedirs with exist_ok=True means it won't crash if the folder already exists, it just moves on, so it acts as a safety meassure

def build_folder_structure(export_path, engine):
# create the right subfolder depending on the engine
    if engine == 'UE': # UNREAL ENGINE
        meshes_folder = os.path.join(export_path, "Content", "Meshes")
    else:  # UNITY
        meshes_folder = os.path.join(export_path, "Assets", "Meshes")

    os.makedirs(meshes_folder, exist_ok=True)  # create folder (and parents) if missing

    return meshes_folder  # hand back the path so the exporter knows where to write

# COLLECT OBJECTS TO EXPORT
def get_objects_to_export(context):
    opts = context.scene.export_options

    if opts.export_mode == 'SELECTED':
        return [obj for obj in context.selected_objects if obj.type == 'MESH']
    else:
        return [obj for obj in context.scene.objects if obj.type == 'MESH']

# MANIFEST JSON WRITER
# this function takes the list of exported mesh info we built up during the export loop and writes it to manifest.json in the root export folder, which UE/Unitity importer script will read

def write_manifest(export_path, engine, exported_meshes):
    # write a manifest.json the engine importer script will read
    content_root = "/Game/Meshes" if engine == 'UE' else "Assets/Meshes"

    manifest = {
        "engine": engine,
        "export_path": export_path,
        "meshes": [
            {
                "file":         os.path.basename(fp),
                "asset_name":   name,
                "content_path": content_root,
                "source_path":  fp,
            }
            for name, fp in exported_meshes
        ]
    }

    manifest_path = os.path.join(export_path, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=4)

    return manifest_path

# CORE EXPORT FUNCTION
# we will call FBX exporter python module directly to avoid problems like context
def export_single_object(obj, file_path, engine):

    # hide everything except our object (temporarilly), we store the original hide state so we can restore it exactly
    hide_states = {o: o.hide_get() for o in bpy.context.scene.objects}

    for o in bpy.context.scene.objects:
        o.hide_set(o.name != obj.name)   # hide all except current obj

    # set up export settings
    if engine == 'UE':
        axis_forward = '-Y'
        axis_up      = 'Z'
    else:  # UNITY
        axis_forward = 'Z'
        axis_up      = 'Y'

    # call the FBX exporter module directly, this is what bpy.ops.export_scene.fbx calls internally, but without needing any ui context at all
    try:
        from io_scene_fbx import export_fbx_bin

        export_fbx_bin.save(
            operator=None,          # no operator needed
            context=bpy.context,    # just pass the global context
            filepath=file_path,

            # what to export
            use_selection=False,    # we controlled visibility above, so export all visible
            use_visible=True,       # export only visible objects (our one mesh)
            use_active_collection=False,
            use_mesh_modifiers=True,

            # axis
            axis_forward=axis_forward,
            axis_up=axis_up,

            # scale
            apply_unit_scale=True, # convert blender scaling to real world scaling 
            apply_scale_options='FBX_SCALE_ALL',
            global_scale=1.0,

            # mesh settings
            mesh_smooth_type='FACE',
            use_tspace=True,

            # animation / bones (we don't need these)
            bake_anim=False,
            add_leaf_bones=False,

            # misc
            path_mode='AUTO',
            embed_textures=False,
        )
        return True

    finally:
        # always restore visibility, even if export failed
        for o, state in hide_states.items():
            o.hide_set(state)

# EXPORT OPERATOR
# operator the export button calls, ties all the helper functions together in the right order

class Export_Scene(bpy.types.Operator):
    bl_idname = "scene.export_scene"
    bl_label  = "Export Scene"

    def execute(self, context):
        opts = context.scene.export_options

        # check export path
        export_path = bpy.path.abspath(opts.export_path)
        if not export_path or not os.path.isdir(export_path):
            self.report({'ERROR'}, "Please set a valid export path first")
            return {'CANCELLED'}

        # collect objects
        objects = get_objects_to_export(context)
        if not objects:
            self.report({'WARNING'}, "No mesh objects found to export")
            return {'CANCELLED'}

        # build folders
        meshes_folder = build_folder_structure(export_path, opts.engine)

        # export each mesh individually
        exported_meshes = []

        for obj in objects:
            file_path = os.path.join(meshes_folder, obj.name + ".fbx")
            try:
                export_single_object(obj, file_path, opts.engine)
                exported_meshes.append((obj.name, file_path))
            except Exception as e:
                self.report({'WARNING'}, f"Failed to export '{obj.name}': {e}")

        if not exported_meshes:
            self.report({'ERROR'}, "No meshes were exported successfully")
            return {'CANCELLED'}

        # write manifest
        write_manifest(export_path, opts.engine, exported_meshes)

        self.report({'INFO'}, f"Exported {len(exported_meshes)} mesh(es) to {meshes_folder}")
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
