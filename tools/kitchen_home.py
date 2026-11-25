# kitchen_home.py: warm kitchen lighting, a window, a door,
# a shallower counter with the sink, and cabinet doors.
# Run once from Unreal's Output Log (Cmd):
#   py "/Users/miclo/Desktop/Git Projects/fruit_fly_game/tools/kitchen_home.py"
# Safe to re-run: it removes what it added last time (tag "RoomExtras") and rebuilds it.

import unreal

ENV = "/Game/FlyGame/Environment"
CUBE = unreal.load_asset("/Engine/BasicShapes/Cube.Cube")
CYLINDER = unreal.load_asset("/Engine/BasicShapes/Cylinder.Cylinder")
TAG = unreal.Name("RoomExtras")

mel = unreal.MaterialEditingLibrary
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
actors_sys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if "Lvl_Kitchen" not in world.get_name():
    raise RuntimeError("Open Lvl_Kitchen first (and stop Play).")


# ---- simple materials ----

def solid_material(name, rgb, metallic=0.0, rough=0.5, glow=0.0, opacity=None):
    path = ENV + "/" + name
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        mel.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, ENV, unreal.Material, unreal.MaterialFactoryNew())

    color = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -500, 0)
    color.set_editor_property("constant", unreal.LinearColor(rgb[0], rgb[1], rgb[2], 1.0))
    mel.connect_material_property(color, "", unreal.MaterialProperty.MP_BASE_COLOR)

    metal = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 150)
    metal.set_editor_property("r", metallic)
    mel.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)

    rough_node = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 250)
    rough_node.set_editor_property("r", rough)
    mel.connect_material_property(rough_node, "", unreal.MaterialProperty.MP_ROUGHNESS)

    if glow > 0:
        light = mel.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -500, 350)
        light.set_editor_property("constant", unreal.LinearColor(rgb[0] * glow, rgb[1] * glow, rgb[2] * glow, 1.0))
        mel.connect_material_property(light, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)

    if opacity is not None:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
        see = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 450)
        see.set_editor_property("r", opacity)
        mel.connect_material_property(see, "", unreal.MaterialProperty.MP_OPACITY)

    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


M_TRIM = solid_material("M_TrimWhite", (0.85, 0.85, 0.82), rough=0.4)
M_HANDLE = solid_material("M_DarkMetal", (0.03, 0.03, 0.03), metallic=1.0, rough=0.35)
M_GLASS = solid_material("M_Glass", (0.75, 0.85, 0.9), rough=0.05, opacity=0.15)
M_GRASS = solid_material("M_Grass", (0.12, 0.3, 0.08), rough=0.9)
M_LAMP = solid_material("M_LampGlow", (1.0, 0.85, 0.65), glow=8.0)
M_WALL = eal.load_asset(ENV + "/M_Wall")
M_WOOD = eal.load_asset(ENV + "/M_Wood")
M_STEEL = eal.load_asset(ENV + "/M_Steel")


def fresh_material(name):
    path = ENV + "/" + name
    if eal.does_asset_exist(path):
        mat = eal.load_asset(path)
        mel.delete_all_material_expressions(mat)
        return mat
    return tools.create_asset(name, ENV, unreal.Material, unreal.MaterialFactoryNew())


def marble_top_material():
    """marble mapped by world position, so the counter pieces line up with no seams"""
    mat = fresh_material("M_MarbleCounter")
    pos = mel.create_material_expression(mat, unreal.MaterialExpressionWorldPosition, -1200, 0)
    xy = mel.create_material_expression(mat, unreal.MaterialExpressionComponentMask, -1000, 0)
    xy.set_editor_property("r", True)
    xy.set_editor_property("g", True)
    xy.set_editor_property("b", False)
    xy.set_editor_property("a", False)
    mel.connect_material_expressions(pos, "", xy, "")
    shrink = mel.create_material_expression(mat, unreal.MaterialExpressionMultiply, -800, 0)
    shrink.set_editor_property("const_b", 1.0 / 900.0)
    mel.connect_material_expressions(xy, "", shrink, "A")
    pic = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -550, 0)
    pic.set_editor_property("texture", eal.load_asset(ENV + "/Marble001_1K-JPG_Color"))
    mel.connect_material_expressions(shrink, "", pic, "UVs")
    mel.connect_material_property(pic, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = mel.create_material_expression(mat, unreal.MaterialExpressionConstant, -550, 250)
    rough.set_editor_property("r", 0.3)
    mel.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


def door_wood_material():
    """same wood, tiled so the grain on a small door matches the big cabinets"""
    mat = fresh_material("M_WoodDoor")
    uv = mel.create_material_expression(mat, unreal.MaterialExpressionTextureCoordinate, -900, 0)
    uv.set_editor_property("u_tiling", 0.65)
    uv.set_editor_property("v_tiling", 0.85)
    pic = mel.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -650, 0)
    pic.set_editor_property("texture", eal.load_asset(ENV + "/Wood051_1K-JPG_Color"))
    mel.connect_material_expressions(uv, "", pic, "UVs")
    mel.connect_material_property(pic, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.recompile_material(mat)
    eal.save_loaded_asset(mat)
    return mat


M_MARBLE_TOP = marble_top_material()
M_WOOD_DOOR = door_wood_material()


# ---- helpers ----

def tag_and_file(actor, name, folder, extra_tags=()):
    actor.set_actor_label(name)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [TAG] + [unreal.Name(t) for t in extra_tags])


def box(name, cx, cy, cz, sx, sy, sz, mat, folder="Kitchen/Room", shadow=True, extra_tags=()):
    """cube centered at (cx, cy, cz), size (sx, sy, sz) in cm"""
    a = actors_sys.spawn_actor_from_object(CUBE, unreal.Vector(cx, cy, cz))
    a.set_actor_scale3d(unreal.Vector(sx / 100.0, sy / 100.0, sz / 100.0))
    comp = a.get_component_by_class(unreal.StaticMeshComponent)
    if mat is not None:
        comp.set_material(0, mat)
    comp.set_cast_shadow(shadow)
    tag_and_file(a, name, folder, extra_tags)
    return a


def ceiling_lamp(name, x, y):
    disc = actors_sys.spawn_actor_from_object(CYLINDER, unreal.Vector(x, y, 2080))
    disc.set_actor_scale3d(unreal.Vector(4.0, 4.0, 0.4))
    comp = disc.get_component_by_class(unreal.StaticMeshComponent)
    comp.set_material(0, M_LAMP)
    comp.set_cast_shadow(False)
    tag_and_file(disc, name + "_Fixture", "Kitchen/Lights")

    light = actors_sys.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, y, 1900))
    lc = light.get_component_by_class(unreal.PointLightComponent)
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    lc.set_intensity(2500.0)
    lc.set_attenuation_radius(6000.0)
    lc.set_editor_property("source_radius", 150.0)
    lc.set_editor_property("use_temperature", True)
    lc.set_editor_property("temperature", 3200.0)
    tag_and_file(light, name, "Kitchen/Lights")


# ---- clear last run ----

REPLACED = ("LeftWall", "CounterTop", "BaseCabinets")
for a in actors_sys.get_all_level_actors():
    label = a.get_actor_label()
    if TAG in a.tags or label in REPLACED or label.startswith("Grapple_Cabinet"):
        actors_sys.destroy_actor(a)

# ---- seal the room so light only comes in through the window ----

for a in actors_sys.get_all_level_actors():
    label = a.get_actor_label()
    if label in ("Ceiling", "FrontWall"):
        a.get_component_by_class(unreal.StaticMeshComponent).set_cast_shadow(True)
    if label == "Sun":
        a.set_actor_rotation(unreal.Rotator(roll=0.0, pitch=-30.0, yaw=15.0), False)

# ---- left wall rebuilt around a window hole ----
# wall: x -3100..-3000, y -2050..550, z -900..2100. hole: y -1300..-100, z 300..1500

box("LeftWall_Bottom", -3050, -750, -300, 100, 2600, 1200, M_WALL)
box("LeftWall_Top", -3050, -750, 1800, 100, 2600, 600, M_WALL)
box("LeftWall_Front", -3050, -1675, 900, 100, 750, 1200, M_WALL)
box("LeftWall_Back", -3050, 225, 900, 100, 650, 1200, M_WALL)

# ---- window: frame, cross bars, glass ----

box("Window_Sill", -3010, -700, 330, 220, 1260, 60, M_TRIM, "Kitchen/Window")
box("Window_Head", -3050, -700, 1470, 140, 1200, 60, M_TRIM, "Kitchen/Window")
box("Window_SideFront", -3050, -1270, 900, 140, 60, 1200, M_TRIM, "Kitchen/Window")
box("Window_SideBack", -3050, -130, 900, 140, 60, 1200, M_TRIM, "Kitchen/Window")
box("Window_BarUp", -3050, -700, 900, 60, 40, 1080, M_TRIM, "Kitchen/Window")
box("Window_BarAcross", -3050, -700, 900, 60, 1080, 40, M_TRIM, "Kitchen/Window")
box("Window_Glass", -3050, -700, 900, 4, 1200, 1200, M_GLASS, "Kitchen/Window", shadow=False)

# ---- grass outside so the window doesn't look into nothing ----

box("OutsideGround", 0, 0, -1100, 60000, 60000, 100, M_GRASS, "Kitchen/Outside")

# ---- door on the right wall (closed, decorative) ----

box("Door", 2990, -1000, 50, 60, 900, 1900, M_TRIM, "Kitchen/Door")
box("Door_Handle", 2945, -620, 0, 30, 150, 30, M_HANDLE, "Kitchen/Door")
box("Door_FrameTop", 2980, -1000, 1030, 80, 1020, 60, M_TRIM, "Kitchen/Door")
box("Door_FrameFront", 2980, -1480, 80, 80, 60, 1960, M_TRIM, "Kitchen/Door")
box("Door_FrameBack", 2980, -520, 80, 80, 60, 1960, M_TRIM, "Kitchen/Door")

# ---- counter: shallower so the sink is reachable ----
# old counter: y -1000..500 (1500 deep). new: y -450..500, built from boxes around the sink hole.
# sink hole: x -1500..-700, y -300..200, bottom at z -280.

C = "Kitchen/Counter"
box("CounterTop_Front", 0, -375, -25, 3600, 150, 50, M_MARBLE_TOP, C)
box("CounterTop_Back", 0, 350, -25, 3600, 300, 50, M_MARBLE_TOP, C)
box("CounterTop_Left", -1650, -50, -25, 300, 500, 50, M_MARBLE_TOP, C)
box("CounterTop_Right", 550, -50, -25, 2500, 500, 50, M_MARBLE_TOP, C)

box("Cabinets_Front", 0, -365, -475, 3560, 130, 850, M_WOOD, C)
box("Cabinets_Back", 0, 340, -475, 3560, 280, 850, M_WOOD, C)
box("Cabinets_Left", -1640, -50, -475, 280, 500, 850, M_WOOD, C)
box("Cabinets_Right", 540, -50, -475, 2480, 500, 850, M_WOOD, C)
box("Cabinets_UnderSink", -1100, -50, -595, 800, 500, 610, M_WOOD, C)

box("Sink_Floor", -1100, -50, -285, 800, 500, 10, M_STEEL, C)
box("Sink_WallFront", -1100, -295, -140, 800, 10, 280, M_STEEL, C)
box("Sink_WallBack", -1100, 195, -140, 800, 10, 280, M_STEEL, C)
box("Sink_WallLeft", -1495, -50, -140, 10, 480, 280, M_STEEL, C)
box("Sink_WallRight", -705, -50, -140, 10, 480, 280, M_STEEL, C)

# ---- cabinet doors: separate wood panels, the gaps read as door lines ----

def door_row(prefix, left, right, cy, cz, height, handle_y, handle_z):
    gap = 20.0
    width = (right - left - 7 * gap) / 6.0
    for i in range(6):
        x0 = left + gap + i * (width + gap)
        box(f"{prefix}Door{i + 1}", x0 + width / 2, cy, cz, width, 15, height, M_WOOD_DOOR, C)
        hx = x0 + width - 40 if i % 2 == 0 else x0 + 40
        box(f"{prefix}Handle{i + 1}", hx, handle_y, handle_z, 20, 15, 150, M_HANDLE, "GrapplePoints",
            extra_tags=("Grapple",))


door_row("Base", -1780, 1780, -437.5, -475, 770, -452.5, -200)
door_row("Upper", -1800, 1800, 92.5, 800, 660, 77.5, 560)

for a in actors_sys.get_all_level_actors():
    if a.get_actor_label() == "DrainCap":
        a.set_actor_location(unreal.Vector(-1100, -50, -278.5), False, False)
    if isinstance(a, unreal.PlayerStart):
        a.set_actor_location(unreal.Vector(-200, -100, 120), False, False)

# ---- warm ceiling lamps ----

ceiling_lamp("CeilingLight_Left", -1500, -750)
ceiling_lamp("CeilingLight_Middle", 0, -750)
ceiling_lamp("CeilingLight_Right", 1500, -750)

# ---- under-cabinet strip light over the counter ----

strip = actors_sys.spawn_actor_from_class(
    unreal.RectLight, unreal.Vector(0, 200, 430), unreal.Rotator(roll=0.0, pitch=-90.0, yaw=0.0))
sc = strip.get_component_by_class(unreal.RectLightComponent)
sc.set_mobility(unreal.ComponentMobility.MOVABLE)
sc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
sc.set_intensity(400.0)
sc.set_attenuation_radius(1500.0)
sc.set_editor_property("source_width", 60.0)
sc.set_editor_property("source_height", 3400.0)
sc.set_editor_property("use_temperature", True)
sc.set_editor_property("temperature", 3000.0)
sc.set_cast_shadows(False)
tag_and_file(strip, "UnderCabinetLight", "Kitchen/Lights")

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
unreal.log_warning("KITCHEN HOME DONE: window, door, lamps, under-cabinet light, new counter, cabinet doors")
