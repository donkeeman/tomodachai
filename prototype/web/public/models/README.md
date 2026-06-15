# Villager / prop models (Blender → glTF)

Drop `.glb` files here and the Babylon client loads them automatically. If a file is
missing, the client falls back to procedural primitive figures, so the game always runs.

## Filenames the client looks for

| File | Used for |
|------|----------|
| `villager_m.glb` | male villagers |
| `villager_f.glb` | female villagers |
| `villager.glb`   | fallback for either gender if the gender-specific file is absent |

(Priority per character: gender file → `villager.glb` → procedural capsule.)

## Blender export settings (glTF 2.0)

1. Model facing **+Z** (the client treats +Z as "forward"), standing on the ground plane
   with feet at the origin (y = 0). Keep it roughly **1.7 units tall** to match the scene scale.
2. `File ▸ Export ▸ glTF 2.0 (.glb/.gltf)`, format **glTF Binary (.glb)**.
3. Transform: **+Y Up** (default). Apply scale/rotation before export
   (`Object ▸ Apply ▸ All Transforms`) to avoid surprises.
4. Include **Skinning + Animations** if the model is rigged. The client auto-plays the
   first animation group (name an idle/loop clip first, e.g. `idle`).
5. Keep materials simple (Principled BSDF, baked/flat colors) for the low-poly look.

## Tips

- Babylon imports glTF natively via `@babylonjs/loaders` (already vendored in `../lib/`).
- For many distinct characters later, export one rigged base mesh and vary color/material,
  or export per-character `.glb` and extend `MODEL_FILES` in `app.js`.
- The plan calls for Blender **MCP** asset generation — those exports land here unchanged.
- Test a model by dropping it in, then reloading the page; the HUD shows `엔진: …+glb`
  when at least one model loaded.
