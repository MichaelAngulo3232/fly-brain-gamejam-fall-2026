"""
build_kitchen.py: builds the greybox kitchen level, Lvl_Kitchen.

Run it inside Unreal (Output Log, Cmd box):
    py "/Users/miclo/Desktop/Git Projects/fruit_fly_game/tools/build_kitchen.py"

Safe to run again: it deletes what it built last time and builds it fresh.
Sizes are in cm. The banana is the size of the template character, so the
kitchen is about 10x real size. The counter top surface is at z = 0.
"""

import unreal

LEVEL = "/Game/FlyGame/Maps/Lvl_Kitchen"
GAME_MODE = "/Game/Variant_Combat/Blueprints/BP_CombatGameMode.BP_CombatGameMode_C"
TAG = "Kitchen"        # on everything this script makes, so a re-run can clear it
GRAPPLE = "Grapple"    # on grapple points, so the grapple ability can find them

CUBE = "/Engine/BasicShapes/Cube"
CYLINDER = "/Engine/BasicShapes/Cylinder"
SPHERE = "/Engine/BasicShapes/Sphere"

# name, shape, center x, center y, bottom z, size x, size y, size z
SHAPES = [
    # room
    ("Floor",         CUBE,         0,  -700, -1000, 6200, 2800,  100),
    ("BackWall",      CUBE,         0,   550,  -900, 6200,  100, 3000),
    ("FrontWall",     CUBE,         0, -2050,  -900, 6200,  100, 3000),
    ("LeftWall",      CUBE,     -3050,  -750,  -900,  100, 2600, 3000),
    ("RightWall",     CUBE,      3050,  -750,  -900,  100, 2600, 3000),
    ("Ceiling",       CUBE,         0,  -750,  2100, 6200, 2800,  100),
    ("BaseCabinets",  CUBE,         0,  -250,  -900, 3560, 1460,  850),
    ("CounterTop",    CUBE,         0,  -250,   -50, 3600, 1500,   50),
    ("UpperCabinets", CUBE,         0,   300,   450, 3600,  400,  700),

    # sink rim and faucet
    ("SinkFront",     CUBE,     -1100,  -315,     0,  860,   30,   60),
    ("SinkBack",      CUBE,     -1100,   215,     0,  860,   30,   60),
    ("SinkLeft",      CUBE,     -1515,   -50,     0,   30,  500,   60),
    ("SinkRight",     CUBE,      -685,   -50,     0,   30,  500,   60),
    ("FaucetPost",    CYLINDER, -1100,   280,     0,   60,   60,  350),
    ("FaucetArm",     CUBE,     -1100,   130,   320,   40,  300,   40),

    # stove
    ("Cooktop",       CUBE,      1100,     0,     0,  800,  600,   10),
    ("Burner1",       CYLINDER,   900,  -150,    10,  200,  200,   20),
    ("Burner2",       CYLINDER,  1300,  -150,    10,  200,  200,   20),
    ("Burner3",       CYLINDER,   900,   150,    10,  200,  200,   20),
    ("Burner4",       CYLINDER,  1300,   150,    10,  200,  200,   20),

    # stuff on the counter
    ("CuttingBoard",  CUBE,       200,  -150,     0,  500,  350,   30),
    ("KnifeBlock",    CUBE,       300,   300,     0,  150,  250,  300),
    ("Toaster",       CUBE,      -300,   320,     0,  300,  200,  220),
    ("CoffeeMug",     CYLINDER,   600,  -250,     0,   80,   80,  100),
    ("FruitBowl",     CYLINDER,  -500,  -250,     0,  250,  250,   80),
    ("SaltShaker",    CYLINDER,   550,   200,     0,   40,   40,  100),
    ("PaperTowels",   CYLINDER,  1650,   350,     0,  110,  110,  280),
    ("CerealBox",     CUBE,     -1650,   330,     0,  200,   70,  300),
]

# name, x, y, z (center). small spheres the banana can grapple to
GRAPPLE_POINTS = [
    ("Grapple_Cabinet1",   -1500,  80, 520),
    ("Grapple_Cabinet2",    -900,  80, 520),
    ("Grapple_Cabinet3",    -300,  80, 520),
    ("Grapple_Cabinet4",     300,  80, 520),
    ("Grapple_Cabinet5",     900,  80, 520),
    ("Grapple_Cabinet6",    1500,  80, 520),
    ("Grapple_Faucet",     -1100, -20, 300),
    ("Grapple_KnifeBlock",   300, 300, 330),
    ("Grapple_PaperTowels", 1650, 350, 310),
]
GRAPPLE_SIZE = 50

# sunlight passes through these, so the room is lit without extra lights
NO_SHADOW = {"FrontWall", "Ceiling"}

levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assets = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)


def tag(actor, name, folder, extra_tags=()):
    actor.set_actor_label(name)
    actor.set_folder_path(folder)
    actor.set_editor_property("tags", [unreal.Name(TAG)] + [unreal.Name(t) for t in extra_tags])
    return actor


def shape(name, mesh, x, y, bottom, sx, sy, sz, folder, extra_tags=()):
    # basic shapes are 100 cm and centered, so: center = bottom + half the height, scale = size / 100
    location = unreal.Vector(x, y, bottom + sz / 2)
    actor = actors.spawn_actor_from_object(unreal.load_asset(mesh), location, unreal.Rotator(0, 0, 0))
    actor.set_actor_scale3d(unreal.Vector(sx / 100, sy / 100, sz / 100))
    return tag(actor, name, folder, extra_tags)


# 1. open the level, or make it the first time
if assets.does_asset_exist(LEVEL):
    levels.load_level(LEVEL)
    for actor in actors.get_all_level_actors():
        if actor.actor_has_tag(TAG):
            actors.destroy_actor(actor)
else:
    levels.new_level(LEVEL)

# 2. lights and sky (all movable, since Lumen and baked lighting are off)
sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, -2000, 3000),
                                    unreal.Rotator(pitch=-40.0, yaw=70.0, roll=0.0))
sun_light = sun.get_component_by_class(unreal.DirectionalLightComponent)
sun_light.set_mobility(unreal.ComponentMobility.MOVABLE)
sun_light.set_editor_property("atmosphere_sun_light", True)
tag(sun, "Sun", "Lighting")

sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 2000), unreal.Rotator(0, 0, 0))
sky_light = sky.get_component_by_class(unreal.SkyLightComponent)
sky_light.set_mobility(unreal.ComponentMobility.MOVABLE)
sky_light.set_editor_property("real_time_capture", True)
tag(sky, "SkyLight", "Lighting")

tag(actors.spawn_actor_from_class(unreal.SkyAtmosphere, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0)),
    "SkyAtmosphere", "Lighting")

# 3. the kitchen
for name, mesh, x, y, bottom, sx, sy, sz in SHAPES:
    actor = shape(name, mesh, x, y, bottom, sx, sy, sz, "Kitchen")
    if name in NO_SHADOW:
        actor.static_mesh_component.set_cast_shadow(False)

for name, x, y, z in GRAPPLE_POINTS:
    shape(name, SPHERE, x, y, z - GRAPPLE_SIZE / 2, GRAPPLE_SIZE, GRAPPLE_SIZE, GRAPPLE_SIZE,
          "GrapplePoints", [GRAPPLE])

# 4. where the banana spawns, and use the combat game mode so it can swing
tag(actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, -600, 120), unreal.Rotator(0, 0, 0)),
    "PlayerStart", "Gameplay")

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
world.get_world_settings().set_editor_property("default_game_mode", unreal.load_class(None, GAME_MODE))

# 5. save
levels.save_current_level()
unreal.log(f"Kitchen built: {len(SHAPES)} shapes, {len(GRAPPLE_POINTS)} grapple points, saved to {LEVEL}")
