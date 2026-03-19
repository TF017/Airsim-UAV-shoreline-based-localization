import unreal
import time
print('RESTART', '='*55)
path=r"/Game/ortophotos/ortophoto_x0_y0_Mat_Inst"
material = unreal.load_asset(path)
print(material.get_class().get_name())
new_material=material
#print(dir(material))


#destination = path.replace('x0', 'x1')
destination = path+r'_lol'
# asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

# # Duplicate as a new MaterialInstanceConstant in Content Browser
# new_material = asset_tools.duplicate_asset(
#     "ortophoto_x1_y0_Mat_Inst",       # New asset name
#     "/Game/ortophotos",      # Destination folder
#     material               # Source asset
# )
# time.sleep(1)
# # Confirm
# print(new_material)
# #print(new_material.get_texture_parameter_source(new_material, 'ortophoto'))
# print(new_material.get_used_textures(new_material))


unreal.EditorAssetLibrary.duplicate_asset(path, destination)
new_material = unreal.load_asset(destination)

#parent = new_material.get_editor_property("parent")

# unreal.MaterialEditingLibrary.recompile_material(parent)

# print(unreal.MaterialEditingLibrary.get_scalar_parameter_names(parent))
# print(unreal.MaterialEditingLibrary.get_vector_parameter_names(parent))
# print(unreal.MaterialEditingLibrary.get_texture_parameter_names(parent))

# print(unreal.MaterialEditingLibrary.get_scalar_parameter_names(new_material),
# unreal.MaterialEditingLibrary.get_vector_parameter_names(new_material),
# unreal.MaterialEditingLibrary.get_texture_parameter_names(new_material))

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

setMaterialInstanceParameter(new_material, 'factor', 109.0)

setMaterialInstanceParameter(new_material, 'ortophoto', unreal.load_asset(r"/Game/ortophotos/ortophoto_x1_y1"))


""" print(unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
    new_material,
    unreal.MaterialEditingLibrary.get_scalar_parameter_names(new_material)[0],
    1009.0
))

texture = unreal.load_asset("/Game/ortophotos/ortophoto_x1_y0")
print(texture)
print(unreal.MaterialEditingLibrary.set_material_instance_texture_parameter_value(
    new_material,
    "ortophoto",
    texture
)) """



unreal.EditorAssetLibrary.save_loaded_asset(new_material, False)
unreal.EditorLevelLibrary.save_all_dirty_levels()
unreal.EditorLevelLibrary.save_current_level()
#unreal.EditorLoadingAndSavingUtils.reload_packages(new_material)
unreal.EditorLevelLibrary.editor_invalidate_viewports()

#print("mat", material)
'''
selected = unreal.unreal.load_asset("/Game/Materials/M_Landscape").get_selected_level_actors()

for actor in selected:

    if isinstance(actor, (unreal.Landscape, unreal.LandscapeStreamingProxy)):

        actor.set_editor_property("landscape_material", material)

        unreal.log(f"Material applied to {actor.get_name()}")

unreal.EditorLevelLibrary.editor_invalidate_viewports()
'''

actors=unreal.EditorLevelLibrary.get_all_level_actors()

for actor in actors:

    if isinstance(actor, (unreal.Landscape, unreal.LandscapeStreamingProxy)):
        loc=actor.get_actor_location()
        if loc.x==0.0 and loc.y==0.0 and loc.z==0.0:
            actor.set_editor_property("landscape_material", new_material)

        #unreal.log(f"Material applied to {actor.get_name()}")

unreal.EditorLevelLibrary.editor_invalidate_viewports()
""" selected = unreal.EditorLevelLibrary.get_selected_level_actors()[0]

print("Dir landscape_material:",dir(selected.landscape_material))
print(selected.landscape_material)
print(selected.landscape_material.texture_parameter_values)

#original=[{"parameter_info": {"name": "ortophoto", "association": GlobalParameter, index: -1}, parameter_value: Texture2D'"/Game/ortophotos/ortophoto_x0_y0.ortophoto_x0_y0"'}]
#new=[{parameter_info: {name: "ortophoto", association: GlobalParameter, index: -1}, parameter_value: Texture2D'"/Game/ortophotos/ortophoto_x0_y1.ortophoto_x0_y1"'}]
#selected.landscape_material.texture_parameter_values=ne

print(dir(selected.landscape_material.texture_parameter_values[0]))
print(selected.landscape_material.texture_parameter_values[0].parameter_value)


paths = unreal.EditorAssetLibrary.list_assets("/Game/", recursive=True)

material_instances = []

for path in paths:
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if isinstance(asset, unreal.Texture):
        material_instances.append(asset)

print(material_instances)

selected.landscape_material.texture_parameter_values[0].set_editor_property('parameter_value', material_instances[10])

print(selected.landscape_material.texture_parameter_values[0].parameter_value) """
