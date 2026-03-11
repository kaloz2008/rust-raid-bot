"""
Rust Raid Calculator Bot — v3
Fixes:
  - Category select stays on chosen category until structure+qty confirmed
  - Corrected all raid costs (None = not possible)
  - Smart mixed recommendation: cheapest sulfur combo per structure
"""

import os
import discord
from discord.ext import commands

# ──────────────────────────────────────────────────────────────────────────────
# RECIPES  (gunpowder per unit, sulfur per unit)
# ──────────────────────────────────────────────────────────────────────────────
RECIPES = {
    "explosive_ammo": (10,   20),
    "rockets":        (1400, 2800),
    "c4":             (2200, 4400),
    "satchels":       (480,  960),
    "fire_arrows":    (0,    10),
}

EXPLOSIVE_LABEL = {
    "explosive_ammo": "💥 Explosive Ammo",
    "rockets":        "🚀 Rockets",
    "c4":             "💣 C4",
    "satchels":       "🎒 Satchel Charges",
    "fire_arrows":    "🔥 Incendiary Arrows",
}

# ──────────────────────────────────────────────────────────────────────────────
# STRUCTURE DATA  (hard side costs, None = not possible / not effective)
# Verified against Rustlabs
# ──────────────────────────────────────────────────────────────────────────────
STRUCTURES = {
    # ── WALLS ─────────────────────────────────────────────────────
    "Wood Wall":                {"explosive_ammo": 46,   "rockets": 2,  "c4": 1, "satchels": 2,  "fire_arrows": 30},
    "Stone Wall":               {"explosive_ammo": 185,  "rockets": 4,  "c4": 2, "satchels": 10, "fire_arrows": None},
    "Metal Wall":               {"explosive_ammo": 500,  "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    "Armored Wall":             {"explosive_ammo": 2000, "rockets": 15, "c4": 8, "satchels": 46, "fire_arrows": None},
    # ── HALF WALLS ────────────────────────────────────────────────
    "Wood Half Wall":           {"explosive_ammo": 23,   "rockets": 1,  "c4": 1, "satchels": 1,  "fire_arrows": 15},
    "Stone Half Wall":          {"explosive_ammo": 95,   "rockets": 2,  "c4": 1, "satchels": 5,  "fire_arrows": None},
    "Metal Half Wall":          {"explosive_ammo": 250,  "rockets": 4,  "c4": 2, "satchels": 12, "fire_arrows": None},
    "Armored Half Wall":        {"explosive_ammo": 1000, "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    # ── FOUNDATIONS ───────────────────────────────────────────────
    "Wood Foundation":          {"explosive_ammo": 46,   "rockets": 2,  "c4": 1, "satchels": 2,  "fire_arrows": 30},
    "Stone Foundation":         {"explosive_ammo": 185,  "rockets": 4,  "c4": 2, "satchels": 10, "fire_arrows": None},
    "Metal Foundation":         {"explosive_ammo": 500,  "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    "Armored Foundation":       {"explosive_ammo": 2000, "rockets": 15, "c4": 8, "satchels": 46, "fire_arrows": None},
    # ── FLOORS ────────────────────────────────────────────────────
    "Wood Floor":               {"explosive_ammo": 46,   "rockets": 2,  "c4": 1, "satchels": 2,  "fire_arrows": 30},
    "Stone Floor":              {"explosive_ammo": 185,  "rockets": 4,  "c4": 2, "satchels": 10, "fire_arrows": None},
    "Metal Floor":              {"explosive_ammo": 500,  "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    "Armored Floor":            {"explosive_ammo": 2000, "rockets": 15, "c4": 8, "satchels": 46, "fire_arrows": None},
    # ── ROOFS ─────────────────────────────────────────────────────
    "Wood Roof":                {"explosive_ammo": 46,   "rockets": 2,  "c4": 1, "satchels": 2,  "fire_arrows": 30},
    "Stone Roof":               {"explosive_ammo": 185,  "rockets": 4,  "c4": 2, "satchels": 10, "fire_arrows": None},
    "Metal Roof":               {"explosive_ammo": 500,  "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    "Armored Roof":             {"explosive_ammo": 2000, "rockets": 15, "c4": 8, "satchels": 46, "fire_arrows": None},
    # ── DOORS ─────────────────────────────────────────────────────
    "Wood Door":                {"explosive_ammo": 18,   "rockets": 1,  "c4": 1, "satchels": 1,  "fire_arrows": 25},
    "Sheet Metal Door":         {"explosive_ammo": 63,   "rockets": 2,  "c4": 1, "satchels": 4,  "fire_arrows": None},
    "Armored Door":             {"explosive_ammo": 250,  "rockets": 4,  "c4": 2, "satchels": 12, "fire_arrows": None},
    "Garage Door":              {"explosive_ammo": 150,  "rockets": 3,  "c4": 2, "satchels": 9,  "fire_arrows": None},
    # ── DOUBLE DOORS ──────────────────────────────────────────────
    "Wood Double Door":         {"explosive_ammo": 36,   "rockets": 2,  "c4": 1, "satchels": 2,  "fire_arrows": 50},
    "Sheet Metal Double Door":  {"explosive_ammo": 126,  "rockets": 3,  "c4": 2, "satchels": 8,  "fire_arrows": None},
    "Armored Double Door":      {"explosive_ammo": 500,  "rockets": 8,  "c4": 4, "satchels": 23, "fire_arrows": None},
    # ── WINDOWS ───────────────────────────────────────────────────
    "Glass Window":             {"explosive_ammo": 1,    "rockets": 1,  "c4": 1, "satchels": 1,  "fire_arrows": 1},
    "Reinforced Window":        {"explosive_ammo": 185,  "rockets": 4,  "c4": 2, "satchels": 10, "fire_arrows": None},
    "Metal Embrasure":          {"explosive_ammo": 63,   "rockets": 2,  "c4": 1, "satchels": 4,  "fire_arrows": None},
    # ── EXTERNAL ──────────────────────────────────────────────────
    "High External Wood Wall":  {"explosive_ammo": 92,   "rockets": 3,  "c4": 2, "satchels": 5,  "fire_arrows": 60},
    "High External Stone Wall": {"explosive_ammo": 370,  "rockets": 7,  "c4": 4, "satchels": 20, "fire_arrows": None},
    "High External Wood Gate":  {"explosive_ammo": 92,   "rockets": 3,  "c4": 2, "satchels": 5,  "fire_arrows": 60},
    "High External Stone Gate": {"explosive_ammo": 370,  "rockets": 7,  "c4": 4, "satchels": 20, "fire_arrows": None},
    # ── HATCHES ───────────────────────────────────────────────────
    "Wood Hatch":               {"explosive_ammo": 18,   "rockets": 1,  "c4": 1, "satchels": 1,  "fire_arrows": 25},
    "Metal Hatch":              {"explosive_ammo": 63,   "rockets": 2,  "c4": 1, "satchels": 4,  "fire_arrows": None},
    "Ladder Hatch":             {"explosive_ammo": 63,   "rockets": 2,  "c4": 1, "satchels": 4,  "fire_arrows": None},
    # ── MISC ──────────────────────────────────────────────────────
    "Floor Grill":              {"explosive_ammo": 30,   "rockets": 1,  "c4": 1, "satchels": 2,  "fire_arrows": None},
}

CATEGORIES = {
    "🧱 Walls & Foundations": [
        "Wood Wall", "Stone Wall", "Metal Wall", "Armored Wall",
        "Wood Half Wall", "Stone Half Wall", "Metal Half Wall", "Armored Half Wall",
        "Wood Foundation", "Stone Foundation", "Metal Foundation", "Armored Foundation",
    ],
    "🪵 Floors & Roofs": [
        "Wood Floor", "Stone Floor", "Metal Floor", "Armored Floor",
        "Wood Roof",  "Stone Roof",  "Metal Roof",  "Armored Roof",
    ],
    "🚪 Doors & Hatches": [
        "Wood Door", "Sheet Metal Door", "Armored Door", "Garage Door",
        "Wood Double Door", "Sheet Metal Double Door", "Armored Double Door",
        "Wood Hatch", "Metal Hatch", "Ladder Hatch",
    ],
    "🖼️ Windows & Misc": [
        "Glass Window", "Reinforced Window", "Metal Embrasure", "Floor Grill",
    ],
    "🏰 External": [
        "High External Wood Wall", "High External Stone Wall",
        "High External Wood Gate", "High External Stone Gate",
    ],
}

CATEGORY_NAMES = list(CATEGORIES.keys())

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def sulfur_cost(exp: str, qty: int) -> int:
    return qty * RECIPES[exp][1]

def cheapest_explosive_for(struct: str) -> str:
    """Return the explosive with lowest sulfur cost for this structure."""
    costs = STRUCTURES[struct]
    best = None
    best_sulfur = 999_999_999
    for exp, (gp, sulfur) in RECIPES.items():
        qty = costs.get(exp)
        if qty is None:
            continue
        s = qty * sulfur
        if s < best_sulfur:
            best_sulfur = s
            best = exp
    return best

def calculate_all(raid_list: list) -> discord.Embed:
    """Full breakdown: every explosive type + totals + mixed recommendation."""
    # Per-explosive totals
    totals = {k: 0 for k in RECIPES}
    for struct, qty in raid_list:
        for exp in RECIPES:
            val = STRUCTURES[struct].get(exp)
            if val is not None:
                totals[exp] += val * qty

    lines = []
    for exp, total in totals.items():
        if total == 0:
            continue
        gp, sulfur = RECIPES[exp]
        line = f"**{EXPLOSIVE_LABEL[exp]}** — `{total:,}` units"
        parts = []
        if gp:     parts.append(f"🪨 `{total*gp:,}` GP")
        if sulfur: parts.append(f"🟡 `{total*sulfur:,}` Sulfur")
        if parts:  line += "\n> " + "  •  ".join(parts)
        lines.append(line)

    # ── MIXED RECOMMENDATION ──────────────────────────────────────────────────
    # For each structure pick the explosive with lowest sulfur cost
    mixed: dict[str, int] = {}   # exp -> total units needed
    mixed_lines = []
    total_mixed_sulfur = 0
    total_mixed_gp     = 0

    for struct, qty in raid_list:
        best_exp = cheapest_explosive_for(struct)
        if best_exp is None:
            mixed_lines.append(f"• {qty}× {struct} — ❌ no explosive works!")
            continue
        units = STRUCTURES[struct][best_exp] * qty
        mixed[best_exp] = mixed.get(best_exp, 0) + units
        s = units * RECIPES[best_exp][1]
        g = units * RECIPES[best_exp][0]
        total_mixed_sulfur += s
        total_mixed_gp     += g
        mixed_lines.append(
            f"• {qty}× **{struct}** → {EXPLOSIVE_LABEL[best_exp]} ×`{units:,}`"
        )

    mixed_summary = []
    for exp, units in mixed.items():
        mixed_summary.append(f"  {EXPLOSIVE_LABEL[exp]}: **{units:,}**")

    embed = discord.Embed(title="🔨 Raid Cost Summary", color=0xe74c3c)

    embed.add_field(
        name="🏗️ Your Raid List",
        value="\n".join(f"• {q}× **{n}**" for n, q in raid_list),
        inline=False,
    )
    embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

    embed.add_field(
        name="💣 If You Use ONE Explosive Type",
        value="\n\n".join(lines) if lines else "—",
        inline=False,
    )
    embed.add_field(name="━━━━━━━━━━━━━━━━━━", value="\u200b", inline=False)

    rec_text = "\n".join(mixed_lines)
    rec_text += "\n\n**You'll need:**\n" + "\n".join(mixed_summary)
    rec_text += f"\n\n🟡 Total Sulfur: **{total_mixed_sulfur:,}**"
    if total_mixed_gp:
        rec_text += f"\n🪨 Total Gunpowder: **{total_mixed_gp:,}**"

    embed.add_field(
        name="🏆 Recommended Mixed Raid (cheapest sulfur per structure)",
        value=rec_text,
        inline=False,
    )

    embed.set_footer(text="⚠️ Hard side costs. Soft side is ~50% cheaper — always face the right side!")
    return embed

# ──────────────────────────────────────────────────────────────────────────────
# MODALS
# ──────────────────────────────────────────────────────────────────────────────

class QuantityModal(discord.ui.Modal, title="How many?"):
    quantity = discord.ui.TextInput(
        label="Quantity",
        placeholder="e.g. 3",
        min_length=1,
        max_length=4,
    )

    def __init__(self, structure: str, session: dict, view: "RaidView"):
        super().__init__(title=f"Add: {structure}")
        self.structure = structure
        self.session   = session
        self._view     = view

    async def on_submit(self, interaction: discord.Interaction):
        raw = self.quantity.value.strip()
        if not raw.isdigit() or int(raw) < 1:
            await interaction.response.send_message("❌ Enter a valid positive number.", ephemeral=True)
            return
        qty = int(raw)
        for i, (name, q) in enumerate(self.session["items"]):
            if name == self.structure:
                self.session["items"][i] = (name, q + qty)
                # reset category select back to prompt
                self._view.reset_selects()
                await interaction.response.edit_message(embed=self._view.build_embed(), view=self._view)
                return
        self.session["items"].append((self.structure, qty))
        self._view.reset_selects()
        await interaction.response.edit_message(embed=self._view.build_embed(), view=self._view)

# ──────────────────────────────────────────────────────────────────────────────
# SELECTS
# ──────────────────────────────────────────────────────────────────────────────

class CategorySelect(discord.ui.Select):
    def __init__(self, view: "RaidView", current: str | None = None):
        self._raid_view = view
        options = [
            discord.SelectOption(label=cat, value=cat, default=(cat == current))
            for cat in CATEGORY_NAMES
        ]
        super().__init__(
            placeholder="① Choose a category…" if not current else f"Category: {current}",
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction):
        chosen = self.values[0]
        self._raid_view.current_category = chosen
        self._raid_view.refresh_structure_select()
        # Keep category visually selected
        self._raid_view.remove_item(self)
        new_cat = CategorySelect(self._raid_view, current=chosen)
        self._raid_view.cat_select = new_cat
        self._raid_view.add_item(new_cat)
        await interaction.response.edit_message(embed=self._raid_view.build_embed(), view=self._raid_view)


class StructureSelect(discord.ui.Select):
    def __init__(self, structures: list, session: dict, view: "RaidView"):
        self._session   = session
        self._raid_view = view
        options = [discord.SelectOption(label=s) for s in structures]
        super().__init__(placeholder="② Pick a structure…", options=options, row=1)

    async def callback(self, interaction: discord.Interaction):
        modal = QuantityModal(self.values[0], self._session, self._raid_view)
        await interaction.response.send_modal(modal)

# ──────────────────────────────────────────────────────────────────────────────
# MAIN VIEW
# ──────────────────────────────────────────────────────────────────────────────

class RaidView(discord.ui.View):
    def __init__(self, session: dict):
        super().__init__(timeout=300)
        self.session          = session
        self.current_category = None

        self.cat_select    = CategorySelect(self, current=None)
        self.struct_select = StructureSelect(CATEGORIES[CATEGORY_NAMES[0]], session, self)

        self.add_item(self.cat_select)
        self.add_item(self.struct_select)

    def refresh_structure_select(self):
        self.remove_item(self.struct_select)
        self.struct_select = StructureSelect(
            CATEGORIES[self.current_category], self.session, self
        )
        self.add_item(self.struct_select)

    def reset_selects(self):
        """Called after quantity confirmed — reset both selects to blank."""
        self.remove_item(self.cat_select)
        self.remove_item(self.struct_select)
        self.current_category = None
        self.cat_select    = CategorySelect(self, current=None)
        self.struct_select = StructureSelect(CATEGORIES[CATEGORY_NAMES[0]], self.session, self)
        self.add_item(self.cat_select)
        self.add_item(self.struct_select)

    def build_embed(self) -> discord.Embed:
        items = self.session["items"]
        desc  = "\n".join(f"• {q}× **{n}**" for n, q in items) if items else "_Nothing added yet._"
        cat_hint = f"**Selected category:** {self.current_category}\n" if self.current_category else ""
        embed = discord.Embed(
            title="🦀 Rust Raid Calculator",
            description=(
                f"{cat_hint}"
                "**① Choose a category**, then **② pick a structure**.\n"
                "A popup will ask for the quantity.\n\n"
                f"**Raid List:**\n{desc}"
            ),
            color=0xe67e22,
        )
        embed.set_footer(text="Press ✅ Calculate when done!")
        return embed

    @discord.ui.button(label="✅ Calculate", style=discord.ButtonStyle.success, row=2)
    async def calc_btn(self, interaction: discord.Interaction, _):
        if not self.session["items"]:
            await interaction.response.send_message("⚠️ Add at least one structure first!", ephemeral=True)
            return
        await interaction.response.send_message(
            embed=calculate_all(self.session["items"]), ephemeral=True
        )

    @discord.ui.button(label="↩️ Undo Last", style=discord.ButtonStyle.secondary, row=2)
    async def undo_btn(self, interaction: discord.Interaction, _):
        if self.session["items"]:
            self.session["items"].pop()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="🗑️ Clear All", style=discord.ButtonStyle.danger, row=2)
    async def clear_btn(self, interaction: discord.Interaction, _):
        self.session["items"].clear()
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

# ──────────────────────────────────────────────────────────────────────────────
# BOT
# ──────────────────────────────────────────────────────────────────────────────

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
    view    = RaidView(session)
    await interaction.response.send_message(embed=view.build_embed(), view=view, ephemeral=True)

@bot.tree.command(name="help", description="Show all bot commands")
async def help_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Rust Raid Bot — Commands", color=0x2ecc71)
    embed.add_field(name="/raid",       value="Interactive raid cost calculator with mixed recommendation.", inline=False)
    embed.add_field(name="/structures", value="List every supported structure type.",                        inline=False)
    embed.add_field(name="/help",       value="Show this message.",                                          inline=False)
    embed.set_footer(text="Hard side costs shown. Soft side is ~50% cheaper!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="structures", description="List all supported structure types")
async def structures_cmd(interaction: discord.Interaction):
    embed = discord.Embed(title="🏗️ Supported Structures", color=0xe67e22)
    for cat, structs in CATEGORIES.items():
        embed.add_field(name=cat, value="\n".join(f"• {s}" for s in structs), inline=True)
    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("ERROR: Set DISCORD_TOKEN.\n  Windows: set DISCORD_TOKEN=your_token_here")
    else:
        bot.run(token)
