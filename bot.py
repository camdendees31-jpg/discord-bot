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

TIMEOUT = aiohttp.ClientTimeout(total=10)  # 10 second timeout on all requests


async def get_roblox_user_id(username: str) -> int | None:
    """Returns Roblox user ID from a username, or None if not found."""
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": False}

    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                return users[0]["id"] if users else None
    except Exception:
        return None


async def owns_gamepass(roblox_user_id: int, gamepass_id: int) -> bool:
    """Returns True if the Roblox user owns the specified gamepass."""
    url = (
        f"https://inventory.roblox.com/v1/users/{roblox_user_id}"
        f"/items/GamePass/{gamepass_id}"
    )
    try:
        async with aiohttp.ClientSession(timeout=TIMEOUT) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return False
                data = await resp.json()
                return len(data.get("data", [])) > 0
    except Exception:
        return False


@client.event
async def on_ready():
    await tree.sync()
    print(f"✅ Logged in as {client.user} — slash commands synced!")


@tree.command(name="verify", description="Verify your Roblox gamepass to get the Supporter role")
@app_commands.describe(roblox_username="Your exact Roblox username")
async def verify(interaction: discord.Interaction, roblox_username: str):
    await interaction.response.defer(ephemeral=True)

    # 1. Look up the Roblox user ID
    roblox_id = await get_roblox_user_id(roblox_username)
    if roblox_id is None:
        await interaction.followup.send(
            f"❌ Could not find a Roblox account with the username **{roblox_username}**. "
            "Please double-check your spelling.",
            ephemeral=True,
        )
        return

    # 2. Check gamepass ownership
    has_pass = await owns_gamepass(roblox_id, GAMEPASS_ID)
    if not has_pass:
        await interaction.followup.send(
            f"❌ **{roblox_username}** does not own the required gamepass, "
            "or their Roblox inventory is set to private. "
            "Make sure your inventory is public and try again.",
            ephemeral=True,
        )
        return

    # 3. Find and assign the Supporter role
    guild = interaction.guild
    role = discord.utils.get(guild.roles, name=SUPPORTER_ROLE_NAME)

    if role is None:
        await interaction.followup.send(
            f"⚠️ Bot error: The **{SUPPORTER_ROLE_NAME}** role doesn't exist in this server. "
            "Please ask an admin to create it.",
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

    await member.add_roles(role, reason=f"Verified Roblox gamepass ownership ({roblox_username})")
    await interaction.followup.send(
        f"🎉 Verified! You've been given the **{SUPPORTER_ROLE_NAME}** role. "
        f"Thanks for your support, **{roblox_username}**!",
        ephemeral=True,
    )


client.run(DISCORD_BOT_TOKEN)
