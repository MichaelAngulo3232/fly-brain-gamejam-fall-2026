// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class fruit_fly_game : ModuleRules
{
	public fruit_fly_game(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] {
			"Core",
			"CoreUObject",
			"Engine",
			"InputCore",
			"EnhancedInput",
			"AIModule",
			"StateTreeModule",
			"GameplayStateTreeModule",
			"UMG",
			"Slate"
		});

		PrivateDependencyModuleNames.AddRange(new string[] { });

		PublicIncludePaths.AddRange(new string[] {
			"fruit_fly_game",
			"fruit_fly_game/Variant_Platforming",
			"fruit_fly_game/Variant_Platforming/Animation",
			"fruit_fly_game/Variant_Combat",
			"fruit_fly_game/Variant_Combat/AI",
			"fruit_fly_game/Variant_Combat/Animation",
			"fruit_fly_game/Variant_Combat/Gameplay",
			"fruit_fly_game/Variant_Combat/Interfaces",
			"fruit_fly_game/Variant_Combat/UI",
			"fruit_fly_game/Variant_SideScrolling",
			"fruit_fly_game/Variant_SideScrolling/AI",
			"fruit_fly_game/Variant_SideScrolling/Gameplay",
			"fruit_fly_game/Variant_SideScrolling/Interfaces",
			"fruit_fly_game/Variant_SideScrolling/UI"
		});

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
