# grapple_handles.py: cabinet handles become the grapple points.
# Deletes the 6 round Grapple_Cabinet spheres, tags every cabinet handle "Grapple",
# and moves the handles into the GrapplePoints folder. Safe to run again.
# Run from Unreal's Output Log (Cmd):
#   py "/Users/miclo/Desktop/Git Projects/fruit_fly_game/tools/grapple_handles.py"

import unreal

actors_sys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
GRAPPLE = unreal.Name("Grapple")

removed = []
tagged = []
with unreal.ScopedEditorTransaction("Handles become grapple points"):
    for a in actors_sys.get_all_level_actors():
        label = a.get_actor_label()
        if label.startswith("Grapple_Cabinet"):
            removed.append(label)
            actors_sys.destroy_actor(a)
        elif label.startswith(("BaseHandle", "UpperHandle")):
            tags = list(a.tags)
            a.modify()
            if GRAPPLE not in tags:
                a.set_editor_property("tags", tags + [GRAPPLE])
            a.set_folder_path("GrapplePoints")
            tagged.append(label)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, False)
unreal.log_warning(f"GRAPPLE HANDLES DONE: removed {len(removed)} spheres, tagged {len(tagged)} handles")
