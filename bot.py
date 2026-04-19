import discord
from discord import app_commands
import aiohttp
import asyncio
import os

# ─────────────────────────────────────────────
#  CONFIG — Edit these values before running
# ─────────────────────────────────────────────
DISCORD_BOT_TOKEN   = os.environ["DISCORD_BOT_TOKEN"]
GAMEPASS_ID         = 1800245516       # ← Replace with your Roblox Gamepass ID
SUPPORTER_ROLE_NAME = "Supporter"     # ← Must match the role name in your server exactly
# ─────────────────────────────────────────────

intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def _check_gamepass(roblox_user_id: int, gamepass_id: int) -> bool:
    url = (
        f"https://inventory.roblox.com/v1/users/{roblox_user_id}"
        f"/items/GamePass/{gamepass_id}"
    )
    timeout = aiohttp.ClientTimeout(total=8)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            print(f"Roblox API status: {resp.status}")
            if resp.status != 200:
                return False
            data = await resp.json()
            print(f"Roblox API response: {data}")
            return len(data.get("data", [])) > 0


async def owns_gamepass(roblox_user_id: int, gamepass_id: int) -> str:
    """Returns 'yes', 'no', or 'error'."""
    try:
        result = await asyncio.wait_for(_check_gamepass(roblox_user_id, gamepass_id), timeout=10)
        return "yes" if result else "no"
    except asyncio.TimeoutError:
        print("Roblox API timed out")
        return "error"
    except Exception as e:
        print(f"Roblox API error: {e}")
        return "error"


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user} — slash commands synced!")


@tree.command(name="verify", description="Verify your Roblox gamepass to get the Supporter role")
@app_commands.describe(roblox_id="Your Roblox User ID (found in your profile URL)")
async def verify(interaction: discord.Interaction, roblox_id: str):
    await interaction.response.defer(ephemeral=True)

    # 1. Validate the ID is a number
    if not roblox_id.strip().isdigit():
        await interaction.followup.send(
            "❌ That doesn't look like a valid Roblox User ID. "
            "It should be a number — find it in your Roblox profile URL: "
            "`roblox.com/users/`**YOUR_ID**`/profile`",
            ephemeral=True,
        )
        return

    user_id = int(roblox_id.strip())

    # 2. Check gamepass ownership
    result = await owns_gamepass(user_id, GAMEPASS_ID)

    if result == "error":
        await interaction.followup.send(
            "⚠️ Could not reach the Roblox API right now. "
            "Please make sure your **Roblox inventory is set to public** "
            "(Roblox Settings → Privacy → Inventory → Everyone), then try again in a moment.",
            ephemeral=True,
        )
        return

    if result == "no":
        await interaction.followup.send(
            f"❌ Roblox account `{user_id}` does not own the required gamepass. "
            "If your inventory is private, set it to **Everyone** in Roblox Privacy Settings.",
            ephemeral=True,
        )
        return

    # 3. Find and assign the Supporter role
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=SUPPORTER_ROLE_NAME)

    if role is None:
        await interaction.followup.send(
            f"⚠️ Bot error: The **{SUPPORTER_ROLE_NAME}** role doesn't exist in this server. "
            "Please create it and try again.",
            ephemeral=True,
        )
        return

    member = interaction.user
    if role in member.roles:
        await interaction.followup.send(
            f"✅ You already have the **{SUPPORTER_ROLE_NAME}** role!",
            ephemeral=True,
        )
        return

    await member.add_roles(role, reason=f"Verified Roblox gamepass ownership (ID: {user_id})")
    await interaction.followup.send(
        f"🎉 Verified! You've been given the **{SUPPORTER_ROLE_NAME}** role. Thanks for your support!",
        ephemeral=True,
    )


client.run(DISCORD_BOT_TOKEN)
