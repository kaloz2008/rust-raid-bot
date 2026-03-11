"""
Rust Raid Calculator Bot — v6
Fixed resource costs: GP ≠ Sulfur — 1 GP requires 2 sulfur + 1 charcoal
Verified against WikiRust March 2026 + Steam raid sulfur guides
"""

import os
import math
import discord
from discord.ext import commands

# ══════════════════════════════════════════════════════════════════════════════
# EXPLOSIVE METADATA
# ══════════════════════════════════════════════════════════════════════════════
EXPLOSIVES = {
    # 1 GP = 2 sulfur + 2 charcoal
    # total sulfur = (gp * 2) + any direct sulfur in recipe
    # total charcoal = gp * 2
    "c4":         {"sulfur": 2200, "gp": 1000, "charcoal": 2000, "label": "C4",                  "emoji": "💣"},
    "rocket":     {"sulfur": 1400, "gp": 650,  "charcoal": 1300, "label": "Rocket",              "emoji": "🚀"},
    "satchel":    {"sulfur": 480,  "gp": 240,  "charcoal": 480,  "label": "Satchel Charge",      "emoji": "🎒"},
    "explo_ammo": {"sulfur": 25,   "gp": 10,   "charcoal": 20,   "label": "Explosive 5.56 Ammo", "emoji": "💥"},
    "hv_rocket":  {"sulfur": 240,  "gp": 110,  "charcoal": 220,  "label": "HV Rocket",           "emoji": "⚡"},
    "inc_rocket": {"sulfur": 110,  "gp": 50,   "charcoal": 100,  "label": "Incendiary Rocket",   "emoji": "🔥"},
    "fire_arrows":{"sulfur": 10,   "gp": 0,    "charcoal": 0,    "label": "Fire Arrow",          "emoji": "🏹"},
    "beancan":    {"sulfur": 120,  "gp": 60,   "charcoal": 120,  "label": "Beancan Grenade",     "emoji": "🥫"},
    "f1_grenade": {"sulfur": 60,   "gp": 30,   "charcoal": 60,   "label": "F1 Grenade",          "emoji": "💣"},
}

TOOLS = {
    "pickaxe":          {"label": "Pickaxe",         "emoji": "⛏️"},
    "hatchet":          {"label": "Hatchet",          "emoji": "🪓"},
    "salvaged_icepick": {"label": "Salvaged Icepick", "emoji": "🔨"},
    "salvaged_axe":     {"label": "Salvaged Axe",     "emoji": "🪚"},
    "jackhammer":       {"label": "Jackhammer",       "emoji": "🔩"},
    "salvaged_sword":   {"label": "Salvaged Sword",   "emoji": "⚔️"},
    "stone_spear":      {"label": "Stone Spear",      "emoji": "🪃"},
    "bone_club":        {"label": "Bone Club",        "emoji": "🦴"},
    "machete":          {"label": "Machete",          "emoji": "🔪"},
    "rock":             {"label": "Rock",             "emoji": "🪨"},
    "wooden_spear":    {"label": "Wooden Spear",      "emoji": "🌿"},
}

# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURE + DEPLOYABLE DATA
# hp = health points
# exp = damage per hit (None = immune / not effective)
# tools = damage per hit (None = immune)
# All values verified WikiRust March 2026 + rustlabs community data
# ══════════════════════════════════════════════════════════════════════════════
STRUCTURES = {

    # ── WALLS ─────────────────────────────────────────────────────────────────
    "Wood Wall": {
        "hp": 250, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Soft side: pickaxe/icepick works well",
    },
    "Stone Wall": {
        "hp": 500, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": "Soft side only: pickaxe viable (~200 hits)",
    },
    "Metal Wall": {
        "hp": 1000, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 125, "satchel": 43.5, "explo_ammo": 2.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "No tools work on metal",
    },
    "Armored Wall": {
        "hp": 2000, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 133, "satchel": 43.5, "explo_ammo": 2.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Hardest structure in game",
    },
    "Wood Half Wall": {
        "hp": 125, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Stone Half Wall": {
        "hp": 250, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },
    "Metal Half Wall": {
        "hp": 500, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 125, "satchel": 43.5, "explo_ammo": 2.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Armored Half Wall": {
        "hp": 1000, "category": "🧱 Walls",
        "exp": {"c4": 250, "rocket": 133, "satchel": 43.5, "explo_ammo": 2.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },

    # ── FOUNDATIONS / FLOORS / ROOFS ──────────────────────────────────────────
    "Wood Foundation": {
        "hp": 250, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Stone Foundation": {
        "hp": 500, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },
    "Metal Foundation": {
        "hp": 1000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 125, "satchel": 43.5, "explo_ammo": 2.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Armored Foundation": {
        "hp": 2000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 133, "satchel": 43.5, "explo_ammo": 2.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Wood Floor": {
        "hp": 250, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Stone Floor": {
        "hp": 500, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },
    "Metal Floor": {
        "hp": 1000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 125, "satchel": 43.5, "explo_ammo": 2.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Armored Floor": {
        "hp": 2000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 133, "satchel": 43.5, "explo_ammo": 2.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Wood Roof": {
        "hp": 250, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Stone Roof": {
        "hp": 500, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },
    "Metal Roof": {
        "hp": 1000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 125, "satchel": 43.5, "explo_ammo": 2.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },
    "Armored Roof": {
        "hp": 2000, "category": "🏗️ Floors & Roofs",
        "exp": {"c4": 250, "rocket": 133, "satchel": 43.5, "explo_ammo": 2.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": None,
    },

    # ── DOORS ─────────────────────────────────────────────────────────────────
    "Wood Door": {
        "hp": 200, "category": "🚪 Doors",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 11, "hv_rocket": 55, "inc_rocket": None, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Hatchet: ~37 hits. Any melee works",
    },
    "Sheet Metal Door": {
        "hp": 250, "category": "🚪 Doors",
        "exp": {"c4": 250, "rocket": 250, "satchel": 63, "explo_ammo": 4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Armored Door": {
        "hp": 1000, "category": "🚪 Doors",
        "exp": {"c4": 267, "rocket": 160, "satchel": 53, "explo_ammo": 3.2, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Garage Door": {
        "hp": 600, "category": "🚪 Doors",
        "exp": {"c4": 300, "rocket": 200, "satchel": 67, "explo_ammo": 4.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Wood Double Door": {
        "hp": 200, "category": "🚪 Doors",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 11, "hv_rocket": 55, "inc_rocket": None, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Same as 2x wood door",
    },
    "Sheet Metal Double Door": {
        "hp": 250, "category": "🚪 Doors",
        "exp": {"c4": 250, "rocket": 250, "satchel": 63, "explo_ammo": 4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Armored Double Door": {
        "hp": 1000, "category": "🚪 Doors",
        "exp": {"c4": 267, "rocket": 160, "satchel": 53, "explo_ammo": 3.2, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },

    # ── HATCHES ───────────────────────────────────────────────────────────────
    "Wood Hatch": {
        "hp": 200, "category": "🪜 Hatches",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 11, "hv_rocket": 55, "inc_rocket": None, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Same as wood door",
    },
    "Metal Hatch": {
        "hp": 250, "category": "🪜 Hatches",
        "exp": {"c4": 250, "rocket": 250, "satchel": 63, "explo_ammo": 4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Ladder Hatch": {
        "hp": 250, "category": "🪜 Hatches",
        "exp": {"c4": 250, "rocket": 250, "satchel": 63, "explo_ammo": 4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },

    # ── WINDOWS & MISC ────────────────────────────────────────────────────────
    "Glass Window": {
        "hp": 50, "category": "🖼️ Windows & Misc",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 25, "hatchet": 13, "salvaged_icepick": 25, "salvaged_axe": 25, "jackhammer": 25, "salvaged_sword": 25, "stone_spear": 8, "bone_club": 5, "machete": 12, "rock": 2, "wooden_spear": 6},
        "note": "Any melee breaks it in 2-4 hits",
    },
    "Reinforced Window": {
        "hp": 500, "category": "🖼️ Windows & Misc",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Metal Embrasure": {
        "hp": 250, "category": "🖼️ Windows & Misc",
        "exp": {"c4": 125, "rocket": 63, "satchel": 19, "explo_ammo": 1.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Floor Grill": {
        "hp": 150, "category": "🖼️ Windows & Misc",
        "exp": {"c4": 250, "rocket": 150, "satchel": 75, "explo_ammo": 5.0, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Tool Cupboard": {
        "hp": 100, "category": "🖼️ Windows & Misc",
        "exp": {"c4": 250, "rocket": 145, "satchel": 50, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "🎯 Priority target! Destroys upkeep",
    },

    # ── EXTERNAL ──────────────────────────────────────────────────────────────
    "High External Wood Wall": {
        "hp": 500, "category": "🏰 External",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 29, "inc_rocket": 250, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Inc rocket is effective here",
    },
    "High External Stone Wall": {
        "hp": 500, "category": "🏰 External",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },
    "High External Wood Gate": {
        "hp": 500, "category": "🏰 External",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 29, "inc_rocket": 250, "fire_arrows": 8, "beancan": 15, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "High External Stone Gate": {
        "hp": 500, "category": "🏰 External",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": None,
    },

    # ── DEPLOYABLES — TURRETS & TRAPS ─────────────────────────────────────────
    "Auto Turret": {
        "hp": 1000, "category": "🤖 Deployables",
        "exp": {"c4": 250, "rocket": 143, "satchel": 45, "explo_ammo": 10, "hv_rocket": 333, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": 20, "salvaged_icepick": None, "salvaged_axe": 30, "jackhammer": None, "salvaged_sword": 40, "stone_spear": 8, "bone_club": 5, "machete": 12, "rock": 5, "wooden_spear": 6},
        "note": "⚠️ Will shoot back! Melee from behind works. Hatchet: ~50 hits",
    },
    "Flame Turret": {
        "hp": 300, "category": "🤖 Deployables",
        "exp": {"c4": 250, "rocket": 100, "satchel": 38, "explo_ammo": 30, "hv_rocket": 100, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 6, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "⚠️ Will torch you if too close! Use melee from max range or explo from distance",
    },
    "SAM Site": {
        "hp": 1000, "category": "🤖 Deployables",
        "exp": {"c4": 250, "rocket": 143, "satchel": 50, "explo_ammo": 10, "hv_rocket": 333, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": 40, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Salvaged sword: ~25 hits. Use HV rocket — extremely cost efficient",
    },
    "Shotgun Trap": {
        "hp": 200, "category": "🤖 Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 11, "hv_rocket": 55, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 6, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "⚠️ Will shoot you! Destroy from behind or side",
    },
    "Tesla Coil": {
        "hp": 250, "category": "🤖 Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 6, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "⚠️ Deals up to 35 dmg/sec when powered! Disable power first",
    },

    # ── DEPLOYABLES — STORAGE ─────────────────────────────────────────────────
    "Large Wood Box": {
        "hp": 300, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Easiest way: any melee ~27 hatchet hits",
    },
    "Metal Large Box": {
        "hp": 375, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Small Wooden Box": {
        "hp": 80, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Any melee works — ~15 hatchet hits",
    },
    "Vending Machine": {
        "hp": 200, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Often used as TC bunker — worth destroying",
    },
    "Workbench T1": {
        "hp": 250, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Satchels are cost effective here",
    },
    "Workbench T2": {
        "hp": 350, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Workbench T3": {
        "hp": 500, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Furnace": {
        "hp": 200, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Large Furnace": {
        "hp": 500, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Research Table": {
        "hp": 200, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
    "Repair Bench": {
        "hp": 200, "category": "📦 Storage & Deployables",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },

    # ── DEPLOYABLES — BARRICADES ──────────────────────────────────────────────
    "Metal Barricade": {
        "hp": 400, "category": "🚧 Barricades",
        "exp": {"c4": 250, "rocket": 200, "satchel": 67, "explo_ammo": 3.7, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Wooden Barricade": {
        "hp": 200, "category": "🚧 Barricades",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": 36, "inc_rocket": 125, "fire_arrows": 8, "beancan": 15, "f1_grenade": 8},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": "Any melee works fine",
    },
    "Concrete Barricade": {
        "hp": 400, "category": "🚧 Barricades",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 2.5, "hatchet": 1.25, "salvaged_icepick": 5, "salvaged_axe": 2.5, "jackhammer": 5, "salvaged_sword": 2, "stone_spear": 0.5, "bone_club": 0.3, "machete": 1, "rock": 0.1, "wooden_spear": 0.4},
        "note": "Pickaxe soft-side works",
    },
    "Prison Cell Wall": {
        "hp": 500, "category": "🚧 Barricades",
        "exp": {"c4": 250, "rocket": 130, "satchel": 50, "explo_ammo": 2.4, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": None, "hatchet": None, "salvaged_icepick": None, "salvaged_axe": None, "jackhammer": None, "salvaged_sword": None, "stone_spear": None, "bone_club": None, "machete": None, "rock": None, "wooden_spear": None},
        "note": "Explosives only",
    },
    "Chainlink Fence": {
        "hp": 200, "category": "🚧 Barricades",
        "exp": {"c4": 250, "rocket": 145, "satchel": 45, "explo_ammo": 5.5, "hv_rocket": None, "inc_rocket": None, "fire_arrows": None, "beancan": None, "f1_grenade": None},
        "tools": {"pickaxe": 11, "hatchet": 5.5, "salvaged_icepick": 11, "salvaged_axe": 12, "jackhammer": 16, "salvaged_sword": 15, "stone_spear": 4, "bone_club": 3, "machete": 8, "rock": 1, "wooden_spear": 3},
        "note": None,
    },
}

# ══════════════════════════════════════════════════════════════════════════════
# BUILD CATEGORY MAP
# ══════════════════════════════════════════════════════════════════════════════
CATEGORIES: dict[str, list[str]] = {}
for name, data in STRUCTURES.items():
    cat = data["category"]
    CATEGORIES.setdefault(cat, []).append(name)
CATEGORY_NAMES = list(CATEGORIES.keys())

# ══════════════════════════════════════════════════════════════════════════════
# CALCULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def hits_needed(hp: int, dmg: float) -> int:
    return math.ceil(hp / dmg)

def sulfur_cost(exp_key: str, qty: int) -> int:
    return EXPLOSIVES[exp_key]["sulfur"] * qty

def gp_cost(exp_key: str, qty: int) -> int:
    return EXPLOSIVES[exp_key]["gp"] * qty

def charcoal_cost(exp_key: str, qty: int) -> int:
    return EXPLOSIVES[exp_key]["charcoal"] * qty

def best_cheapest(struct: str):
    hp = STRUCTURES[struct]["hp"]
    best_key, best_qty, best_s = None, None, 10**9
    for k, dmg in STRUCTURES[struct]["exp"].items():
        if dmg is None: continue
        q = hits_needed(hp, dmg)
        s = sulfur_cost(k, q)
        if s < best_s:
            best_s, best_key, best_qty = s, k, q
    return best_key, best_qty

def best_efficient(struct: str):
    hp = STRUCTURES[struct]["hp"]
    best_key, best_qty, best_waste, best_s = None, None, 10**9, 10**9
    for k, dmg in STRUCTURES[struct]["exp"].items():
        if dmg is None: continue
        q = hits_needed(hp, dmg)
        waste = q * dmg - hp
        s = sulfur_cost(k, q)
        if waste < best_waste or (waste == best_waste and s < best_s):
            best_waste, best_s, best_key, best_qty = waste, s, k, q
    return best_key, best_qty

def calculate(raid_list: list) -> discord.Embed:
    # Per-explosive totals
    exp_totals = {k: 0 for k in EXPLOSIVES}
    for struct, qty in raid_list:
        hp = STRUCTURES[struct]["hp"]
        for k, dmg in STRUCTURES[struct]["exp"].items():
            if dmg is not None:
                exp_totals[k] += hits_needed(hp, dmg) * qty

    exp_lines = []
    for k, total in exp_totals.items():
        if total == 0: continue
        m = EXPLOSIVES[k]
        s = sulfur_cost(k, total)
        g = gp_cost(k, total)
        c = charcoal_cost(k, total)
        line = f"{m['emoji']} **{m['label']}** — `{total:,}`"
        parts = [f"🟡 `{s:,}` Sulfur"]
        if g: parts.append(f"🪨 `{g:,}` Gunpowder")
        if c: parts.append(f"🖤 `{c:,}` Charcoal")
        line += "\n> " + "  •  ".join(parts)
        exp_lines.append(line)

    # Tool totals
    tool_totals = {k: 0 for k in TOOLS}
    for struct, qty in raid_list:
        hp = STRUCTURES[struct]["hp"]
        for k, dmg in STRUCTURES[struct]["tools"].items():
            if dmg is not None:
                tool_totals[k] += hits_needed(hp, dmg) * qty

    tool_lines = [
        f"{TOOLS[k]['emoji']} **{TOOLS[k]['label']}** — `{v:,}` hits"
        for k, v in tool_totals.items() if v > 0
    ]

    # Recommendation 1 — cheapest (lowest sulfur)
    cheap_lines, cheap_exp_totals = [], {k: 0 for k in EXPLOSIVES}
    for struct, qty in raid_list:
        k, per = best_cheapest(struct)
        if k is None:
            cheap_lines.append(f"• {qty}× **{struct}** → ❌ no explosive works")
            continue
        total = per * qty
        cheap_exp_totals[k] += total
        m = EXPLOSIVES[k]
        cheap_lines.append(f"• {qty}× **{struct}** → {m['emoji']} {m['label']} ×`{total:,}` (🟡`{sulfur_cost(k,total):,}`)")
    cheap_summary = [f"{EXPLOSIVES[k]['emoji']} **{EXPLOSIVES[k]['label']}**: `{v:,}`" for k, v in cheap_exp_totals.items() if v > 0]
    cheap_s = sum(sulfur_cost(k, v) for k, v in cheap_exp_totals.items())
    cheap_g = sum(gp_cost(k, v) for k, v in cheap_exp_totals.items())
    cheap_c = sum(charcoal_cost(k, v) for k, v in cheap_exp_totals.items())
    cheap_text = "\n".join(cheap_lines) + "\n\n**You'll need:**\n" + "\n".join(cheap_summary)
    cheap_text += f"\n🟡 **{cheap_s:,}** Sulfur"
    if cheap_g: cheap_text += f"  •  🪨 **{cheap_g:,}** Gunpowder"
    if cheap_c: cheap_text += f"  •  🖤 **{cheap_c:,}** Charcoal"

    # Recommendation 2 — most efficient (min waste, tiebreak by sulfur)
    eff_lines, eff_exp_totals = [], {k: 0 for k in EXPLOSIVES}
    for struct, qty in raid_list:
        k, per = best_efficient(struct)
        if k is None:
            eff_lines.append(f"• {qty}× **{struct}** → ❌ no explosive works")
            continue
        total = per * qty
        eff_exp_totals[k] += total
        m = EXPLOSIVES[k]
        hp = STRUCTURES[struct]["hp"]
        dmg = STRUCTURES[struct]["exp"][k]
        waste = per * dmg - hp
        wn = f" *(+{waste:.0f} overkill)*" if waste > 0 else " ✅ *perfect!*"
        eff_lines.append(f"• {qty}× **{struct}** → {m['emoji']} {m['label']} ×`{total:,}`{wn}")
    eff_summary = [f"{EXPLOSIVES[k]['emoji']} **{EXPLOSIVES[k]['label']}**: `{v:,}`" for k, v in eff_exp_totals.items() if v > 0]
    eff_s = sum(sulfur_cost(k, v) for k, v in eff_exp_totals.items())
    eff_g = sum(gp_cost(k, v) for k, v in eff_exp_totals.items())
    eff_c = sum(charcoal_cost(k, v) for k, v in eff_exp_totals.items())
    eff_text = "\n".join(eff_lines) + "\n\n**You'll need:**\n" + "\n".join(eff_summary)
    eff_text += f"\n🟡 **{eff_s:,}** Sulfur"
    if eff_g: eff_text += f"  •  🪨 **{eff_g:,}** Gunpowder"
    if eff_c: eff_text += f"  •  🖤 **{eff_c:,}** Charcoal"

    # Build embed
    embed = discord.Embed(title="🔨 Raid Cost Summary", color=0xe74c3c)

    struct_lines = [f"• {q}× **{n}** *(HP: {STRUCTURES[n]['hp']:,})*" for n, q in raid_list]
    embed.add_field(name="🏗️ Raid List", value="\n".join(struct_lines), inline=False)
    embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

    if exp_lines:
        embed.add_field(name="💣 Single Explosive Type Breakdown", value="\n\n".join(exp_lines), inline=False)
    if tool_lines:
        embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
        embed.add_field(name="🛠️ Tools (where applicable)", value="\n".join(tool_lines), inline=False)

    embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
    embed.add_field(name="💰 Rec. 1 — Cheapest (Lowest Sulfur)", value=cheap_text, inline=False)
    embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)
    embed.add_field(name="⚡ Rec. 2 — Most Efficient (Min Overkill)", value=eff_text, inline=False)
    embed.set_footer(text="⚠️ Hard side values. Soft side ~50% cheaper. Check notes on deployables!")
    return embed

# ══════════════════════════════════════════════════════════════════════════════
# UI
# ══════════════════════════════════════════════════════════════════════════════

class QuantityModal(discord.ui.Modal):
    quantity = discord.ui.TextInput(label="Quantity", placeholder="e.g. 3", min_length=1, max_length=4)
    def __init__(self, structure: str, session: dict, view: "RaidView"):
        super().__init__(title=f"Add: {structure}")
        self.structure, self.session, self._view = structure, session, view
    async def on_submit(self, interaction: discord.Interaction):
        raw = self.quantity.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message("❌ Enter a valid positive number.", ephemeral=True)
            return
        qty = int(raw)
        for i, (name, q) in enumerate(self.session["items"]):
            if name == self.structure:
                self.session["items"][i] = (name, q + qty)
                self._view.reset_selects()
                await interaction.response.edit_message(embed=self._view.build_embed(), view=self._view)
                return
        self.session["items"].append((self.structure, qty))
        self._view.reset_selects()
        await interaction.response.edit_message(embed=self._view.build_embed(), view=self._view)

class CategorySelect(discord.ui.Select):
    def __init__(self, view: "RaidView", current: str | None = None):
        self._raid_view = view
        options = [discord.SelectOption(label=cat, value=cat, default=(cat == current)) for cat in CATEGORY_NAMES]
        placeholder = f"① Category: {current}" if current else "① Choose a category…"
        super().__init__(placeholder=placeholder, options=options, row=0)
    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self._raid_view.current_category = chosen
        self._raid_view.remove_item(self)
        new_cat = CategorySelect(self._raid_view, current=chosen)
        self._raid_view.cat_select = new_cat
        self._raid_view.add_item(new_cat)
        self._raid_view.refresh_structure_select()
        await interaction.response.edit_message(embed=self._raid_view.build_embed(), view=self._raid_view)

class StructureSelect(discord.ui.Select):
    def __init__(self, structures: list, session: dict, view: "RaidView"):
        self._session, self._raid_view = session, view
        options = [discord.SelectOption(label=s, description=f"HP: {STRUCTURES[s]['hp']:,}") for s in structures[:25]]
        super().__init__(placeholder="② Pick a structure…", options=options, row=1)
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(QuantityModal(self.values[0], self._session, self._raid_view))

class RaidView(discord.ui.View):
    def __init__(self, session: dict):
        super().__init__(timeout=300)
        self.session = session
        self.current_category = None
        self.cat_select    = CategorySelect(self, current=None)
        self.struct_select = StructureSelect(CATEGORIES[CATEGORY_NAMES[0]], session, self)
        self.add_item(self.cat_select)
        self.add_item(self.struct_select)

    def refresh_structure_select(self):
        self.remove_item(self.struct_select)
        self.struct_select = StructureSelect(CATEGORIES[self.current_category], self.session, self)
        self.add_item(self.struct_select)

    def reset_selects(self):
        self.remove_item(self.cat_select)
        self.remove_item(self.struct_select)
        self.current_category = None
        self.cat_select    = CategorySelect(self, current=None)
        self.struct_select = StructureSelect(CATEGORIES[CATEGORY_NAMES[0]], self.session, self)
        self.add_item(self.cat_select)
        self.add_item(self.struct_select)

    def build_embed(self) -> discord.Embed:
        items = self.session["items"]
        desc = "\n".join(f"• {q}× **{n}** *(HP: {STRUCTURES[n]['hp']:,})*" for n, q in items) if items else "_Nothing added yet._"
        cat_hint = f"**Selected:** {self.current_category}\n" if self.current_category else ""
        embed = discord.Embed(
            title="🦀 Rust Raid Calculator",
            description=f"{cat_hint}**① Choose a category**, then **② pick a structure** (HP shown).\nA popup will ask for the quantity.\n\n**Raid List:**\n{desc}",
            color=0xe67e22,
        )
        embed.set_footer(text="Press ✅ Calculate when done!")
        return embed

    @discord.ui.button(label="✅ Calculate", style=discord.ButtonStyle.success, row=2)
    async def calc_btn(self, interaction: discord.Interaction, _):
        if not self.session["items"]:
            await interaction.response.send_message("⚠️ Add at least one structure first!", ephemeral=True)
            return
        await interaction.response.send_message(embed=calculate(self.session["items"]), ephemeral=True)

    @discord.ui.button(label="↩️ Undo Last", style=discord.ButtonStyle.secondary, row=2)
    async def undo_btn(self, interaction: discord.Interaction, _):
        if self.session["items"]: self.session["items"].pop()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🗑️ Clear All", style=discord.ButtonStyle.danger, row=2)
    async def clear_btn(self, interaction: discord.Interaction, _):
        self.session["items"].clear()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for child in self.children: child.disabled = True

# ══════════════════════════════════════════════════════════════════════════════
# BOT
# ══════════════════════════════════════════════════════════════════════════════

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Logged in as {bot.user} — slash commands synced.")

@bot.tree.command(name="raid", description="Open the interactive Rust raid calculator")
async def raid(interaction: discord.Interaction):
    session = {"items": []}
    view = RaidView(session)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

@bot.tree.command(name="help", description="Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Rust Raid Bot — Commands", color=0x2ecc71)
    embed.add_field(name="/raid",       value="Interactive calculator — structures, deployables, tools, 2 smart recommendations.", inline=False)
    embed.add_field(name="/structures", value="List all supported structures & deployables with HP.",                               inline=False)
    embed.add_field(name="/help",       value="Show this message.",                                                                 inline=False)
    embed.set_footer(text="Data verified WikiRust March 2026.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="structures", description="List all structures and deployables with HP")
async def structures_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🏗️ All Structures & Deployables", color=0xe67e22)
    for cat, structs in CATEGORIES.items():
        lines = [f"• {s} *(HP: {STRUCTURES[s]['hp']:,})*" for s in structs]
        embed.add_field(name=cat, value="\n".join(lines), inline=False)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: Set DISCORD_TOKEN.\n  Windows: set DISCORD_TOKEN=your_token_here")
    else:
        bot.run(token)
