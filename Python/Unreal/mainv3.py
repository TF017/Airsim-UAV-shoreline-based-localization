import unreal
import gc
import os
import re
import time

unreal.EditorLevelLibrary.save_all_dirty_levels()
unreal.EditorLevelLibrary.save_current_level()
unreal.SystemLibrary.collect_garbage()
gc.collect()

TILE_RE = re.compile(r"(x\d+_y\d+)", re.IGNORECASE)
MIC_DST = "/Game/Geo/MaterialsInstances"    # onde criar as material instances
PATH=r"C:\Users\Tiago Ferreira\Documents\airsim_shoreline_localization\Python\MDTmerger\ortophotos"
TEXTURE_DST = "/Game/Geo/Textures"           # onde importar as texturas
TILE_SIZE=1009
RESOLUTION=0.5 #in meters (OF THE ORTOPHOTOS)
TILE_SIZE_ADJUSTED=TILE_SIZE*RESOLUTION*100
BASE_MATERIAL_INSTANCE="/Game/BASE_Inst"
MAX_LEVELS_LOADED=50
N=8

# ---------------- HELPERS ----------------
def log(msg):
    unreal.log("[ORTHO] " + msg)

def warn(msg):
    unreal.log_warning("[ORTHO] " + msg)

def tile_key_from_name(name: str):
    m = TILE_RE.search(name.replace("-", "_"))
    return m.group(1).lower() if m else None

def getMaterialInstanceParameters(material_instance, parameters):
    param_names = []
    for param_info in parameters:
        str_name = str(param_info.parameter_info.name)
        if str_name:
            param_names.append(str_name)

    return param_names


def setMaterialInstanceParameter(material_instance, param_name, param_value):
    param_info = unreal.MaterialParameterInfo(name=unreal.Name(param_name), association=unreal.MaterialParameterAssociation.GLOBAL_PARAMETER, index=-1)

    if type(param_value) == float:
        parameters = material_instance.scalar_parameter_values
        parameter = unreal.ScalarParameterValue(parameter_info=param_info, parameter_value=param_value)
    if type(param_value) == unreal.LinearColor:
        parameters = material_instance.vector_parameter_values
        parameter = unreal.VectorParameterValue(parameter_info=param_info, parameter_value=param_value)
    if type(param_value) == unreal.Texture2D:
        parameters = material_instance.texture_parameter_values
        parameter = unreal.TextureParameterValue(parameter_info=param_info, parameter_value=param_value)

    parameter_names = getMaterialInstanceParameters(material_instance, parameters)

    if param_name not in parameter_names:
        #todo: check if the parameter exists in the parent material: parent_material = material_instance.parent.get_base_material()
        parameters.append(parameter)
    else:
        for i in range(len(parameters)):
            if parameters[i].parameter_info.name == param_name:
                new_params = parameters[i].copy() #struct copy
                new_params.parameter_value = param_value
                parameters[i] = new_params               

    return parameters

def ensure_dir(asset_dir: str):
    if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
        unreal.EditorAssetLibrary.make_directory(asset_dir)

def load_or_create_mic(mic_name: str, master_mat):
    asset_path = f"{MIC_DST}/{mic_name}"

    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        mic = unreal.EditorAssetLibrary.load_asset(asset_path)
    else:
        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        factory = unreal.MaterialInstanceConstantFactoryNew()
        mic = asset_tools.create_asset(
            mic_name,
            MIC_DST,
            unreal.MaterialInstanceConstant,
            factory
        )
        if mic is None:
            raise RuntimeError(f"Não consegui criar MIC: {asset_path}")

    unreal.MaterialEditingLibrary.set_material_instance_parent(mic, master_mat)
    return mic



#import ortofotos
def import_texture(file_path: str):
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

    asset_name = os.path.splitext(os.path.basename(file_path))[0]

    task = unreal.AssetImportTask()
    task.set_editor_property("automated", True)
    task.set_editor_property("destination_path", TEXTURE_DST)
    task.set_editor_property("destination_name", asset_name)
    task.set_editor_property("filename", file_path)
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("save", True)

    tex_factory = unreal.TextureFactory()
    tex_factory.set_editor_property("create_material", False)
    task.set_editor_property("factory", tex_factory)

    asset_tools.import_asset_tasks([task])

    imported_paths = list(task.get_editor_property("imported_object_paths"))
    if not imported_paths:
        raise RuntimeError(f"Falhou a importação de {file_path}")

    tex = unreal.EditorAssetLibrary.load_asset(imported_paths[0])
    if tex is None:
        raise RuntimeError(f"Não consegui carregar a textura importada: {imported_paths[0]}")

    return tex


def all_landscape_proxies():
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    return [a for a in actors if isinstance(a, unreal.LandscapeStreamingProxy)]

def round(x): return int(x%1>0.45)+int(x)

def main():
    proxies=all_landscape_proxies()
    material = unreal.load_asset(BASE_MATERIAL_INSTANCE)
    ensure_dir(MIC_DST)
    for proxy in proxies:
            # tenta obter a key do actor label; se falhar, usa o nome interno
            actor_position = proxy.get_actor_location()
            x,y=actor_position.x, actor_position.y
            #print(x/TILE_SIZE_ADJUSTED, y/TILE_SIZE_ADJUSTED)
            real_x=round(x/TILE_SIZE_ADJUSTED)
            real_y=round(y/TILE_SIZE_ADJUSTED)
            name="x"+str(real_x)+"_y"+str(real_y)
            #log("Proxie with "+name)
            destination=MIC_DST+"/MIC_"+name
            unreal.EditorAssetLibrary.duplicate_asset(BASE_MATERIAL_INSTANCE, destination)
            new_material = unreal.load_asset(destination)
            setMaterialInstanceParameter(new_material, 'factor', float(TILE_SIZE))
            texture=TEXTURE_DST +"/ortophoto_"+name
            #print(texture)
            #print(unreal.load_asset(texture))
            setMaterialInstanceParameter(new_material, 'orto', unreal.load_asset(texture))
            #log('done')
            unreal.EditorAssetLibrary.save_loaded_asset(new_material, False)
            proxy.set_editor_property("landscape_material", new_material)
            unreal.EditorLevelLibrary.save_all_dirty_levels()
            unreal.EditorLevelLibrary.save_current_level()
            unreal.EditorLevelLibrary.editor_invalidate_viewports()
            unreal.SystemLibrary.collect_garbage()
            gc.collect()
    #print('Load another landscape proxies') 
        
#main()

#levels = ["/Game/StarterContent/Maps/heightmap/heightmap_x%d_y%d" % (i, j) for i in range(0, MAX_X) for j in range(0,MAX_Y)]


def load_levels():
    levels_list=composite_list[N]
    levels=[]
    for level_path in levels_list:
        #print(f"Processing {level_path}")
        levels.append(unreal.EditorLevelUtils.add_level_to_world(
            world,
            level_path,
            unreal.LevelStreamingDynamic
        ))
    main()
    unreal.EditorLevelLibrary.save_all_dirty_levels()
    unreal.EditorLevelLibrary.save_current_level()
    unreal.EditorLevelLibrary.editor_invalidate_viewports()
    unreal.SystemLibrary.collect_garbage()
    gc.collect()
    for level in levels: #This does not work is best to close manually
        level.set_is_requesting_unload_and_removal(True)
        level.set_editor_property("should_be_loaded", False)

    #unreal.EditorLoadingAndSavingUtils.load_map(level_path)

    # Save after processing
    #unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

    # Unload level
    #level = unreal.EditorLevelLibrary.get_level(level_path)
    #unreal.EditorLevelLibrary.remove_level_from_world(level)

if N==0:
    ensure_dir(TEXTURE_DST)
    for file in os.listdir(PATH):
        if file[-4:]=='.png':
            file_path=os.path.join(PATH, file)
            tex=import_texture(file_path)

#unreal.EditorLoadingAndSavingUtils.load_map("/Game/StarterContent/Maps/Minimal_Default.Minimal_Default")
asset_registry = unreal.AssetRegistryHelpers.get_asset_registry()

maps = asset_registry.get_assets_by_class("World")

world = unreal.EditorLevelLibrary.get_editor_world()

filtered_maps = [
    a.object_path for a in maps
    if str(a.package_name).startswith("/Game/StarterContent/Maps/heightmap/")
]
composite_list = [filtered_maps[x:min(len(filtered_maps)-1,x+MAX_LEVELS_LOADED)] for x in range(0, len(filtered_maps),MAX_LEVELS_LOADED)]
#print(composite_list)
log("You have N=%d, until N=%d" % (N, len(composite_list)-1))
load_levels()

unreal.EditorLevelLibrary.save_all_dirty_levels()
unreal.EditorLevelLibrary.save_current_level()
unreal.EditorLevelLibrary.editor_invalidate_viewports()
unreal.SystemLibrary.collect_garbage()
gc.collect()
unreal.EditorLevelLibrary.save_all_dirty_levels()
unreal.EditorLevelLibrary.save_current_level()
