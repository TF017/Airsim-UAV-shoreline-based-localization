import unreal
import os
import re

# ---------------- CONFIG ----------------
PATCH_DIR = r"C:\Users\Tiago Ferreira\Documents\airsim_shoreline_localization\Python\MDTmerger\Ortophotos"                 # pasta no disco com os PNGs
TEXTURE_DST = "/Game/Geo/Textures"           # onde importar as texturas
MIC_DST = "/Game/Geo/Materials/Instances"    # onde criar as material instances
MASTER_MAT_PATH = "/Game/Geo/M_Landscape_Ortho"
TEXTURE_PARAM = "OrthoTex"

# Extrai algo como x12_y7 de nomes tipo:
#   patch_x12_y7.png
#   LandscapeStreamingProxy_x12_y7
#   Tile_x12_y7
TILE_RE = re.compile(r"(x\d+_y\d+)", re.IGNORECASE)


# ---------------- HELPERS ----------------
def log(msg):
    unreal.log("[ORTHO] " + msg)

def warn(msg):
    unreal.log_warning("[ORTHO] " + msg)

def tile_key_from_name(name: str):
    m = TILE_RE.search(name.replace("-", "_"))
    return m.group(1).lower() if m else None

def ensure_dir(asset_dir: str):
    if not unreal.EditorAssetLibrary.does_directory_exist(asset_dir):
        unreal.EditorAssetLibrary.make_directory(asset_dir)

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

def all_landscape_proxies():
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    return [a for a in actors if isinstance(a, unreal.LandscapeStreamingProxy)]


# ---------------- MAIN ----------------
def main():
    ensure_dir(TEXTURE_DST)
    ensure_dir(MIC_DST)

    master_mat = unreal.EditorAssetLibrary.load_asset(MASTER_MAT_PATH)
    if master_mat is None:
        raise RuntimeError(f"Material-base não encontrado: {MASTER_MAT_PATH}")

    # 1) importa todos os PNGs e indexa por key x#_y#
    textures_by_key = {}

    for fname in os.listdir(PATCH_DIR):
        if not fname.lower().endswith(".png"):
            continue

        key = tile_key_from_name(fname)
        if key is None:
            warn(f"Nome sem key de tile, ignorado: {fname}")
            continue

        fpath = os.path.join(PATCH_DIR, fname)
        tex = import_texture(fpath)
        textures_by_key[key] = tex
        log(f"Textura importada: {fname} -> {key}")

    # 2) percorre proxies carregados e aplica material instance por tile
    proxies = all_landscape_proxies()
    log(f"Landscape proxies carregados: {len(proxies)}")

    assigned = 0
    missing = []

    for proxy in proxies:
        # tenta obter a key do actor label; se falhar, usa o nome interno
        actor_label = proxy.get_actor_label()
        actor_name = proxy.get_name()

        key = tile_key_from_name(actor_label) or tile_key_from_name(actor_name)
        if key is None:
            warn(f"Proxy sem key reconhecível: label={actor_label} name={actor_name}")
            continue

        tex = textures_by_key.get(key)
        if tex is None:
            missing.append(key)
            warn(f"Sem textura para tile {key}")
            continue

        mic_name = f"MI_Ortho_{key}"
        mic = load_or_create_mic(mic_name, master_mat)

        ok = unreal.BlueprintMaterialTextureNodesBPLibrary.set_mic_texture_param_editor_only(
            mic, TEXTURE_PARAM, tex
        )
        if not ok:
            raise RuntimeError(f"Falhou set_mic_texture_param_editor_only em {mic_name}")

        unreal.EditorAssetLibrary.save_loaded_asset(mic)

        proxy.set_editor_property("landscape_material", mic)
        assigned += 1
        log(f"Atribuído {mic_name} ao proxy {actor_label}")

    # 3) guarda níveis alterados
    unreal.EditorLevelLibrary.save_all_dirty_levels()

    log(f"Concluído. Proxies actualizados: {assigned}")
    if missing:
        warn("Tiles sem patch: " + ", ".join(sorted(set(missing))))


if __name__ == "__main__":
    main()