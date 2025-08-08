Waysprites Taming Script v1.3 🐾

This document explains how to set up and use the Waysprites Taming v1.3 script. It’s designed for Ultima Online using Razor Enhanced and aims to take your Animal Taming skill from around 30 to the Grandmaster range while healing you and your pets and keeping things tidy. You don’t need to know how to code — just read the configuration section and adjust a few values to suit your playstyle.



Overview 🧭
🔍 Searches for creatures near you and picks targets that match your skill level. It walks up to them, uses Animal Taming, and reacts to success or failure.
📖 Shows advice when your skill enters a new bracket. The messages suggest which animals to tame and where to find them based on the comprehensive tameables list
tamingarchive.com.
🔖 Renames and releases tamed pets. Successful pets get renamed (default WayPet) and then freed if they exceed your follower count. It handles the two different release gumps found in various zones and only stops when the pet is truly gone.
🩹 Heals you and your pets. Choose which methods you want to use (Magery, bandages, potions, etc.). You can list the serials of your favourite pets so the script keeps them alive with veterinary or spell healing. It also cures poison and resurrects pets when needed.
🧹 Keeps your follower slots clear. It automatically kills leftover training pets named like your rename value within 10 tiles, so they don’t clutter up your follower count.
⚡ Defends against aggressive mobs. If a red/orange enemy hits you, the script casts Lightning to deter it (you can disable this if you prefer).



File Layout 📂
The script is contained in one .py file. It’s broken down into sections:
Imports and user configuration: near the top, after the imports, you’ll see USER CONFIGURATION. This is where you change names, healing flags, timers, and your pet serial numbers. Everything in this section is safe to edit.
Helpers and data: the next sections inline helpers from enemies.py and tameables.py, so you don’t need any external files.
Functions: functions for healing (heal_player, heal_pets), advice (send_taming_advice), target selection (FindAnimalToTame), releasing pets (TryReleasePet), and the main loop (TrainAnimalTaming).
Auto-run: at the bottom, the script calls TrainAnimalTaming() automatically when executed.

You don’t need to understand the functions to use the script, but advanced users can customise them to handle special cases (e.g. custom tamables or different release gumps).



Configuration Options 🛠️
All the settings you’re likely to change live under ### USER CONFIGURATION ###. They’re grouped by category and documented in plain English. Below is a summary of each group.

General taming options 🐾
🏷️ renameTamedAnimalsTo: The nickname given to every new pet. It’s a single word; default is WayPet. Changing this will also change which pets get auto-cleaned.
🙈 petsToIgnore: A list of names the script will never target. Keep your rename value here so it doesn’t try to tame or rename your own training pets.
👥 numberOfFollowersToKeep: How many followers you want to keep after a tame. If you exceed this number, the newest pet will be released.
🔁 maximumTameAttempts: How many times to attempt to tame each creature. 0 means keep trying until you succeed or move on.
🎯 minimumTamingDifficulty: The script ignores creatures below this difficulty. Increase it to focus on harder animals once you’ve moved past farm stock.
🚀 prioritizeHardestNearby: When True, the script will try to tame the toughest animal it can see (even if slightly above your skill). When False, it only picks animals you can currently tame.

Healing options ❤️
🩺 Healing flags (healUsingMagery, healUsingBandages, healUsingChivalry, healUsingSpiritSpeak, healUsingMysticism, healUsingSpellweaving, healUsingPotions, healUsingBushido): Turn these True for the methods you can use. The script tries them in a sensible order, stopping at the first success.

❤️ healThreshold: Heal yourself when your HP drops below this fraction of your maximum. For example, 0.5 heals at 50 %.

Behaviour toggles 🎮
🎵 enablePeacemaking: Reserved for future features; leave off unless you add barding logic.
🚶 enableFollowAnimal: If the target is beyond your taming range, follow it until you’re close enough.
🧹 purgeLeftoverPets: Kill stray pets named like your training pet (WayPet) within 10 tiles to free follower slots.
⚔️ autoDefendAgainstAggro: Cast Lightning on aggressive mobs (reds/oranges) when they hit you.



Timer configuration ⏱️ (milliseconds)
⏳ noAnimalsToTrainTimerMilliseconds: How long to wait when no animals are found before scanning again.
🏃 playerStuckTimerMilliseconds: How long to wait before the script decides the player is stuck and tries to move.
🏇 catchUpToAnimalTimerMilliseconds: How long to follow an animal before giving up.
⏰ animalTamingTimerMilliseconds: How long to wait for taming feedback before timing out and moving on.
💤 targetClearDelayMilliseconds: A short pause after clearing a target queue.

Cleanup configuration 🗑️
killOnSightPetNames: Derived from your rename value (WayPet by default). Any pet with a matching name is culled when found nearby.

Pet healing configuration 🐾
🐕 PET_SERIALS: List the serial numbers of your own pets (tank or follower pets). The script will monitor these pets and heal or resurrect them as needed.
🩹 BANDAGE_TYPE: The item ID for veterinary bandages; 0x0E21 is standard.
🧑‍⚕️ VET_REZ_THRESHOLD & PET_HEAL_THRESHOLD: When a pet’s HP drops below 5 %, the script will attempt to resurrect; below 25 % it will heal.
🔄 REMINDER_INTERVAL, DISTANCE_MSG_INTERVAL, MSG_INTERVAL: Control how often the script reminds you about bandages or warns you if your pet is too far away.
📏 MAGE_HEAL_RANGE & VET_RANGE: Maximum distances (in tiles) at which Magery healing or bandaging is allowed.

How to Use the Script 🧾
🧑‍🌾 Prepare your character. Buy your Animal Taming skill up to around 30 from an NPC stable master (most shards allow this). Get some bandages and a spellbook if you’re enabling Magery.
📂 Copy the file to your Razor Enhanced Scripts folder. You can name it anything; the script auto-runs when executed.
📝 Open the file in a text editor and go to the USER CONFIGURATION section. Adjust options to match your shard, animals, and healing methods. Save the file.
▶️ Start Razor Enhanced and run the script. Right-click on the script name and choose Play.
👀 Watch the in-game messages. The script announces what it’s doing: whether it found an animal, whether it’s taming, what to target next, and when your skill enters a new bracket (based on training guidelines
tamingarchive.com
). It renames successful tames and releases them automatically.
🦄 Move on to harder animals as you level up. Use the advice messages as a guide; you generally want animals whose minimum taming skill is within about 5 points of your current skill for optimal gains
uoforever.com.

Testing New Builds & Adjustments 🧪
🔬 Test in a controlled area first, like a farm. Ensure the script tames cows, goats, and sheep correctly before trying harder creatures.
🗂️ Check the release behaviour. When a pet is tamed and renamed, the script opens the context menu and clicks the Release entry. Some zones show a “destroy pet” dialog; others show a “set free” dialog. The script reads the gump text to decide which button to press. Watch the gump to confirm it presses the correct button and stops when the pet disappears.
🧑‍⚕️ Confirm pet healing by letting one of your pets take damage. The script should cast Greater Heal or bandage it when its HP drops below 25 % (as per PET_HEAL_THRESHOLD). If the pet dies, it should resurrect at 5 %.
🎯 Adjust minimumTamingDifficulty if the script either wastes time on easy animals or ignores too many. For example, when you first move to 65–75 skill, set it around 65 so it will pick bulls, grey wolves and panthers
tamingarchive.com. Then gradually raise it as you progress.
⏳ Watch the timers. If the script seems to hang when taming something (no journal messages appear), it uses animalTamingTimerMilliseconds to time out and move on. Tune these values if you see it either rushing or waiting too long.
📑 Read the logs. Razor Enhanced’s console will display any exceptions or errors. A common error is a context menu mismatch; if release fails repeatedly, adjust the release logic in TryReleasePet to match your shard’s context menus.

Troubleshooting & Tips 🛠️
💤 Nothing happens when I run the script. Make sure you saved your configuration changes and that your healing flags match your abilities. Check that you have bandages or mana. Also ensure the script file is actually running (the console will print messages).
🔁 It keeps trying to tame the same animal forever. The script should time out after 13 seconds (default). If it doesn’t, check your journal filters or UO client messages; the script relies on phrases like “You fail to tame the creature” and “It seems to accept you as master.” If your shard uses different wording, update the journal checks.
😿 My follower pets die while I’m taming. Add their serial numbers to PET_SERIALS. Increase PET_HEAL_THRESHOLD if they’re not getting healed soon enough, and make sure you have bandages in your backpack.
⚡ The script spams Lightning on panthers. Disable autoDefendAgainstAggro if you don’t want auto-attacks. Also note that some animals become hostile when attacked; the script only zaps true aggressors (criminal, enemy or murderer). It shouldn’t target docile creatures.
🔓 Releasing fails on my shard. The script tries context menu indices 9 and 8. If your shard has Release in a different position, change the indices in TryReleasePet. Also expand the gump keyword lists if your dialog uses different phrases.

Goals & Future Features 🌟
🦁 Tank pet & kiting support. The next updates will allow you to pick a powerful pet (e.g. dragon or nightmare) to tank high-end creatures. The script will command it to attack while healing it and keeping you at a safe distance.
🧠 Dynamic difficulty window. Instead of a fixed minimumTamingDifficulty, the script will calculate a skill window around your current skill and pick the hardest creature within that window.
🎶 Peacemaking & barding support. Calm aggressive creatures so you can tame them without taking damage.
🛠️ Shard-specific customisation. Support for different context menu indexes, release gumps and custom creatures; ability to load animal data from a separate file or JSON.

Feedback and contributions are welcome 🤝. Feel free to share experiences from your shard or suggestions for improvements.