"""
Reads the manifest.json produced by the blender Scene Validation Tool
and imports every .fbx into the correct Unreal content path

HOW TO USE:
    1. In Unreal, go to Tools > Execute Python Script
    2. Point it at this file
    3. Set MANIFEST_PATH below to your manifest.json location

    or drop this into your project's Content/Python folder and run it
    from the Unreal Python console: import manifest_reader
"""
import unreal
import json
import os

# CONFIGURATION / set this to your manifest.json path before running
MANIFEST_PATH = "C:/path/to/your/export/manifest.json"

# HELPER FUNCTIONS

def load_manifest(path):
    """Read the manifest.json from the blender exporter."""
    abs_path = os.path.abspath(path)
    if not os.path.isfile(abs_path):
        unreal.log_error(f"[ManifestReader] manifest.json not found at: {abs_path}") # safety meassure
        return None

    with open(abs_path, 'r') as f:
        data = json.load(f)

    unreal.log(f"[ManifestReader] Loaded manifest — engine: {data.get('engine')}, " # load manifest reader and say which engine
               f"{len(data.get('meshes', []))} mesh(es) found") # amount of meshes found to import
    return data


def build_import_task(source_path, content_path, asset_name):
    """
    Build an .fbx import task for a single mesh
    Returns an unreal.AssetImportTask ready to be queued
    """
    task = unreal.AssetImportTask()

    # source fbx on disk
    task.filename     = source_path
    # destination inside the content browser  ex. /Game/Meshes
    task.destination_path = content_path
    # asset name inside unreal
    task.destination_name = asset_name

    task.automated    = True   # no import dialog popups
    task.save         = True   # save the .uasset immediately after import
    task.replace_existing = True  # overwrite if already imported

    # fbx specific options
    options = unreal.FbxImportUI()
    options.import_mesh       = True # im only importing my .fbx meshes
    options.import_textures   = False  # textures handled separately
    options.import_animations = False
    options.import_as_skeletal = False
    options.create_physics_asset = False

    mesh_options = unreal.FbxStaticMeshImportData()
    mesh_options.combine_meshes          = True   # one mesh per file
    mesh_options.auto_generate_collision = True
    mesh_options.generate_lightmap_u_vs  = True
    mesh_options.normal_import_method    = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS

    options.static_mesh_import_data = mesh_options
    task.options = options

    return task


def run_import_tasks(tasks):
    """Execute a list of AssetImportTasks and report results."""
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks(tasks)

    imported     = []
    failed       = []

    for task in tasks:
        if task.imported_object_paths:
            imported.extend(task.imported_object_paths)
        else:
            failed.append(task.filename)

    return imported, failed



# MAIN FUNCTION

def run(manifest_path=MANIFEST_PATH):
    unreal.log("=" * 60)
    unreal.log("[ManifestReader] Starting import...")
    unreal.log("=" * 60)

    # load manifest
    manifest = load_manifest(manifest_path)
    if not manifest:
        return

    meshes = manifest.get("meshes", [])
    if not meshes:
        unreal.log_warning("[ManifestReader] Manifest contains no meshes — nothing to import.")
        return

    # build one import task per mesh entry
    tasks = []
    for entry in meshes:
        source_path  = entry.get("source_path", "")
        asset_name   = entry.get("asset_name",  "")
        content_path = entry.get("content_path", "/Game/Meshes")

        # guard: make sure the fbx actually exists on disk
        if not os.path.isfile(source_path):
            unreal.log_warning(f"[ManifestReader] FBX not found on disk, skipping: {source_path}")
            continue

        tasks.append(build_import_task(source_path, content_path, asset_name))
        unreal.log(f"[ManifestReader] Queued: {asset_name}  ->  {content_path}")

    if not tasks:
        unreal.log_error("[ManifestReader] No valid FBX files to import.")
        return

    # 3. run all tasks in one batch (faster than one-by-one)
    with unreal.ScopedEditorTransaction("Manifest FBX Import") as trans:
        imported, failed = run_import_tasks(tasks)

    # 4. report
    unreal.log("=" * 60)
    unreal.log(f"[ManifestReader] Done!  {len(imported)} imported,  {len(failed)} failed.")

    for path in imported:
        unreal.log(f"  [OK]   {path}")
    for path in failed:
        unreal.log_warning(f"  [FAIL] {path}")

    unreal.log("=" * 60)

# run immediately when executed via Tools > Execute Python Script
run()