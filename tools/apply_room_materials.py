import unreal

ENV = "/Game/FlyGame/Environment"
DISK = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_content_dir()) + "FlyGame/Environment/"
mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()


def get_texture(name, filename):
    path = ENV + "/" + name
    if not eal.does_asset_exist(path):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", DISK + filename)
        task.set_editor_property("destination_path", ENV)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        tools.import_asset_tasks([task])
    tex = eal.load_asset(path)
    if tex is None:
        raise RuntimeError("could not find or import " + filename)
    return tex


def build_material(name, tex, u, v, tint=None):
    path = ENV + "/" + name
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, ENV, unreal.Material, unreal.MaterialFactoryNew())

    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    uv.set_editor_property("u_tiling", u)
    uv.set_editor_property("v_tiling", v)

    pic = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -650, 0)
    pic.set_editor_property("texture", tex)
    mel.connect_material_expressions(uv, "", pic, "UVs")

    if tint is None:
        mel.connect_material_property(pic, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    else:
        color = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -650, 300)
        color.set_editor_property("constant", unreal.LinearColor(tint[0], tint[1], tint[2], 1.0))
        mul = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 100)
        mel.connect_material_expressions(pic, "RGB", mul, "A")
        mel.connect_material_expressions(color, "", mul, "B")
        mel.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)

    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


floor_tex = get_texture("Tiles052_1K-JPG_Color", "Tiles052_1K-JPG_Color.jpg")
wall_tex = get_texture("beige_wall_001_diff_1k", "beige_wall_001_diff_1k.jpg")

m_floor = build_material("M_Floor", floor_tex, 8.0, 3.6)
m_wall = build_material("M_Wall", wall_tex, 3.0, 1.5, tint=(0.65, 0.9, 0.7))

targets = {
    "Floor": m_floor,
    "BackWall": m_wall,
    "FrontWall": m_wall,
    "LeftWall": m_wall,
    "RightWall": m_wall,
}

done = []
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
with unreal.ScopedEditorTransaction("Room materials"):
    for a in actors:
        label = a.get_actor_label()
        if label in targets:
            comp = a.get_component_by_class(unreal.StaticMeshComponent)
            comp.modify()
            comp.set_material(0, targets[label])
            done.append(label)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log_warning("ROOM MATERIALS DONE: " + ", ".join(sorted(done)))
