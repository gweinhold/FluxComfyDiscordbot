import discord
from discord import app_commands
from discord.ext import commands as discord_commands
from Main.custom_commands import views
from config import BOT_MANAGER_ROLE_ID, CHANNEL_IDS
import logging
import os
import sys
import uuid
import time
import sqlite3
from typing import Optional
from config import BOT_MANAGER_ROLE_ID, CHANNEL_IDS
from config import fluxversion

from Main.database import (
    DB_NAME, ban_user, unban_user, get_ban_info, 
    add_banned_word, remove_banned_word,
    get_banned_words, remove_user_warnings,
    get_all_warnings, get_user_warnings
)
from Main.utils import load_json, save_json, generate_random_seed
from Main.custom_commands.views import OptionsView, LoRAView
from Main.custom_commands.models import RequestItem
from Main.custom_commands.banned_utils import check_banned
from Main.custom_commands.workflow_utils import update_workflow

logger = logging.getLogger(__name__)

def has_admin_or_bot_manager_role():
    async def predicate(interaction: discord.Interaction):
        is_admin = interaction.user.guild_permissions.administrator
        has_role = any(role.id == BOT_MANAGER_ROLE_ID for role in interaction.user.roles)
        if is_admin or has_role:
            return True
        await interaction.response.send_message("You don't have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

def in_allowed_channel():
    async def predicate(interaction: discord.Interaction):
        if interaction.channel_id not in CHANNEL_IDS:
            await interaction.response.send_message("This command can only be used in specific channels.", ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

async def notify_admin(bot, user, prompt, is_warning: bool, banned_word: str):
    try:
        for guild in bot.guilds:
            role = discord.utils.get(guild.roles, id=BOT_MANAGER_ROLE_ID)
            if role:
                for member in role.members:
                    # Get warning count if it's a warning
                    warning_info = ""
                    if is_warning:
                        warning_count = get_user_warnings(str(user.id))
                        warning_info = f"Warning {warning_count}/2"
                    
                    notification = (
                        f"{'⚠️ ' + warning_info if is_warning else '🚫 BAN'} NOTIFICATION:\n"
                        f"User: {user.name} (ID: {user.id})\n"
                        f"Prompt: {prompt}\n"
                        f"Banned Word: {banned_word}"
                    )
                    try:
                        await member.send(notification)
                    except discord.Forbidden:
                        continue
                    break
    except Exception as e:
        logger.error(f"Failed to notify admin: {e}")

async def setup_commands(bot: discord.Client):
    @bot.tree.command(name="comfy", description="Generate an image based on a prompt")
    @in_allowed_channel()
    @app_commands.describe(
        prompt="Enter your prompt",
        resolution="Choose the resolution",
        upscale_factor="Choose upscale factor (1-4, default is 1)",
        seed="Enter a seed for reproducibility (optional)"
    )
    @app_commands.choices(resolution=[
        app_commands.Choice(name=name, value=name) 
        for name in load_json('ratios.json')['ratios'].keys()
    ])
    @app_commands.choices(upscale_factor=[
        app_commands.Choice(name=str(i), value=i) for i in range(1, 5)
    ])
    async def comfy(interaction: discord.Interaction, prompt: str, resolution: str, 
                upscale_factor: int = 1, seed: Optional[int] = None):
        try:
            is_banned, message = check_banned(str(interaction.user.id), prompt)
            if "WARNING" in message:  # This is a warning
                await notify_admin(
                    interaction.client,
                    interaction.user,
                    prompt,
                    is_warning=True,
                    banned_word=message.split("'")[1]  # Extract banned word from message
                )
                await interaction.response.send_message(message, ephemeral=True)
                return
            elif is_banned:
                await notify_admin(
                    interaction.client,
                    interaction.user,
                    prompt,
                    is_warning=False,
                    banned_word=message.split("'")[1]  # Extract banned word from message
                )
                await interaction.response.send_message(message, ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            
            view = LoRAView(interaction.client)
            msg = await interaction.followup.send("Please select LoRAs to use:", view=view, ephemeral=True)
            
            await view.wait()
            selected_loras = view.selected_loras
            await msg.delete()
            
            if not hasattr(view, 'has_confirmed'):
                logger.debug("LoRA selection was cancelled or timed out")
                return

            additional_prompts = []
            lora_config = load_json('lora.json')
            for lora in selected_loras:
                lora_info = next((l for l in lora_config['available_loras'] if l['file'] == lora), None)
                if lora_info and lora_info.get('add_prompt'):
                    additional_prompts.append(lora_info['add_prompt'])
            
            full_prompt = f"{prompt} {' '.join(additional_prompts)}".strip()
            
            if seed is None:
                seed = generate_random_seed()

            workflow = load_json(fluxversion)
            request_uuid = str(uuid.uuid4())
            current_timestamp = int(time.time())
            
            workflow = update_workflow(workflow, 
                                f"{full_prompt} (Timestamp: {current_timestamp})", 
                                resolution, 
                                selected_loras, 
                                upscale_factor,
                                seed)

            workflow_filename = f'flux3_{request_uuid}.json'
            save_json(workflow_filename, workflow)

            original_message = await interaction.followup.send("Generating image... 0% complete", ephemeral=False)

            request_item = RequestItem(
                id=str(interaction.id),
                user_id=str(interaction.user.id),
                channel_id=str(interaction.channel.id),
                interaction_id=str(interaction.id),
                original_message_id=str(original_message.id),
                prompt=full_prompt,
                resolution=resolution,
                loras=selected_loras,
                upscale_factor=upscale_factor,
                workflow_filename=workflow_filename,
                seed=seed
            )
            await interaction.client.subprocess_queue.put(request_item)

        except Exception as e:
            logger.error(f"Error in comfy command: {str(e)}", exc_info=True)
            await interaction.followup.send(f"An error occurred: {str(e)}", ephemeral=True)

    @bot.tree.command(name="reboot", description="Reboot the bot (Restricted to specific admin)")
    async def reboot(interaction: discord.Interaction):
        if interaction.user.id == BOT_MANAGER_ROLE_ID:
            await interaction.response.send_message("Rebooting bot...", ephemeral=True)
            await bot.close()
            os.execv(sys.executable, ['python'] + sys.argv)
        else:
            await interaction.response.send_message("You don't have permission.", ephemeral=True)

    @bot.tree.command(name="add_banned_word", description="Add a word to the banned list")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_banned_word_command(interaction: discord.Interaction, word: str):
        word = word.lower()
        add_banned_word(word)  # This calls the database function
        await interaction.response.send_message(f"Added '{word}' to the banned words list.", ephemeral=True)

    @bot.tree.command(name="remove_banned_word", description="Remove a word from the banned list")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_banned_word_command(interaction: discord.Interaction, word: str):
        word = word.lower()
        remove_banned_word(word)  # This calls the database function
        await interaction.response.send_message(f"Removed '{word}' from the banned words list.", ephemeral=True)

    @bot.tree.command(name="list_banned_words", description="List all banned words")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_banned_words(interaction: discord.Interaction):
        banned_words = get_banned_words()
        if banned_words:
            await interaction.response.send_message(f"Banned words: {', '.join(banned_words)}", ephemeral=True)
        else:
            await interaction.response.send_message("There are no banned words.", ephemeral=True)

    @bot.tree.command(name="ban_user", description="Ban a user from using the comfy command")
    @app_commands.checks.has_permissions(administrator=True)
    async def ban_user_command(interaction: discord.Interaction, user: discord.User, reason: str):
        ban_user(str(user.id), reason)
        await interaction.response.send_message(f"Banned {user.name} from using the comfy command. Reason: {reason}", ephemeral=True)

    @bot.tree.command(name="unban_user", description="Unban a user from using the comfy command")
    @app_commands.checks.has_permissions(administrator=True)
    async def unban_user_command(interaction: discord.Interaction, user: discord.User):
        if unban_user(str(user.id)):
            await interaction.response.send_message(f"Unbanned {user.name} from using the comfy command.", ephemeral=True)
        else:
            await interaction.response.send_message(f"{user.name} is not banned from using the comfy command.", ephemeral=True)

    @bot.tree.command(name="whybanned", description="Check why a user was banned")
    @app_commands.checks.has_permissions(administrator=True)
    async def whybanned(interaction: discord.Interaction, user: discord.User):
        ban_info = get_ban_info(str(user.id))
        if ban_info:
            await interaction.response.send_message(
                f"{user.name} was banned on {ban_info['banned_at']} for the following reason: {ban_info['reason']}", 
                ephemeral=True
            )
        else:
            await interaction.response.send_message(f"{user.name} is not banned.", ephemeral=True)

    @bot.tree.command(name="list_banned_users", description="List all banned users")
    @app_commands.checks.has_permissions(administrator=True)
    async def list_banned_users(interaction: discord.Interaction):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT user_id, reason, banned_at FROM banned_users")
        banned_users = c.fetchall()
        conn.close()

        if banned_users:
            banned_list = "\n".join([f"User ID: {user[0]}, Reason: {user[1]}, Banned at: {user[2]}" 
                                   for user in banned_users])
            await interaction.response.send_message(f"Banned users:\n{banned_list}", ephemeral=True)
        else:
            await interaction.response.send_message("There are no banned users.", ephemeral=True)
    
    @bot.tree.command(name="remove_warning", description="Remove all warnings from a user")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_warning_command(interaction: discord.Interaction, user: discord.User):
        try:
            success, message = remove_user_warnings(str(user.id))
            if success:
                await interaction.response.send_message(
                    f"Successfully removed all warnings from {user.name} ({user.id}).\n{message}", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"Could not remove warnings from {user.name} ({user.id}).\n{message}", 
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error in remove_warning command: {str(e)}")
            await interaction.response.send_message(
                f"An error occurred while removing warnings: {str(e)}", 
                ephemeral=True
            )

    @bot.tree.command(name="check_warnings", description="Check all user warnings")
    @app_commands.checks.has_permissions(administrator=True)
    async def check_warnings_command(interaction: discord.Interaction):
        try:
            success, result = get_all_warnings()
            
            if not success:
                await interaction.response.send_message(result, ephemeral=True)
                return
            
            embeds = []
            
            # Create an embed for each user with warnings
            for user_id, warnings in result.items():
                try:
                    # Try to fetch user info
                    user = await interaction.client.fetch_user(int(user_id))
                    user_name = user.name
                except:
                    user_name = f"Unknown User ({user_id})"
                
                embed = discord.Embed(
                    title=f"Warnings for {user_name}",
                    color=discord.Color.yellow()
                )
                embed.set_footer(text=f"User ID: {user_id}")
                
                warning_count = len(warnings)
                if warning_count == 1:
                    status = "🟡 Active - First Warning"
                elif warning_count == 2:
                    status = "🔴 Final Warning"
                else:
                    status = "⚫ Unknown Status"

                embed.add_field(
                    name="Warning Status",
                    value=f"{status}\n{warning_count}/2 warnings",
                    inline=False
                )
                
                for idx, (prompt, word, warned_at) in enumerate(warnings, 1):
                    embed.add_field(
                        name=f"Warning {idx} - {warned_at}",
                        value=f"**Banned Word Used:** {word}\n**Full Prompt:** {prompt}",
                        inline=False
                    )
                embeds.append(embed)
            
            if len(embeds) == 0:
                await interaction.response.send_message("No warnings found in the database.", ephemeral=True)
                return
                
            # If only one embed, send it without navigation
            if len(embeds) == 1:
                await interaction.response.send_message(embed=embeds[0], ephemeral=True)
            else:
                # Create navigation view for multiple embeds
                class NavigationView(discord.ui.View):
                    def __init__(self):
                        super().__init__(timeout=180)  # 3 minute timeout
                        self.current_page = 0

                    @discord.ui.button(label="◀️ Previous", style=discord.ButtonStyle.gray)
                    async def previous_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        if button_interaction.user.id != interaction.user.id:
                            await button_interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
                            return
                        self.current_page = (self.current_page - 1) % len(embeds)
                        embed = embeds[self.current_page]
                        embed.set_footer(text=f"Page {self.current_page + 1}/{len(embeds)}")
                        await button_interaction.response.edit_message(embed=embed)

                    @discord.ui.button(label="Next ▶️", style=discord.ButtonStyle.gray)
                    async def next_button(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                        if button_interaction.user.id != interaction.user.id:
                            await button_interaction.response.send_message("You cannot use these buttons.", ephemeral=True)
                            return
                        self.current_page = (self.current_page + 1) % len(embeds)
                        embed = embeds[self.current_page]
                        embed.set_footer(text=f"Page {self.current_page + 1}/{len(embeds)}")
                        await button_interaction.response.edit_message(embed=embed)

                    async def on_timeout(self):
                        # Disable buttons after timeout
                        for item in self.children:
                            item.disabled = True
                        # Try to update the message with disabled buttons
                        try:
                            await interaction.edit_original_response(view=self)
                        except:
                            pass

                view = NavigationView()
                first_embed = embeds[0]
                first_embed.set_footer(text=f"Page 1/{len(embeds)}")
                await interaction.response.send_message(embed=first_embed, view=view, ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in check_warnings command: {str(e)}")
            await interaction.response.send_message(
                f"An error occurred while checking warnings: {str(e)}", 
                ephemeral=True
            )
            

    @bot.tree.command(name="sync", description="Sync bot commands")
    @has_admin_or_bot_manager_role()
    async def sync_commands(interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            synced = await bot.tree.sync()
            await interaction.followup.send(f"Synced {len(synced)} commands.")
            logger.info(f"Synced {len(synced)} commands")
        except discord.app_commands.errors.CheckFailure as e:
            logger.error(f"Check failure in sync_commands: {str(e)}", exc_info=True)
            await interaction.response.send_message("You don't have permission to use this command.", 
                                                  ephemeral=True)
        except Exception as e:
            logger.error(f"Error in sync_commands: {str(e)}", exc_info=True)
            await interaction.followup.send(f"An error occurred: {str(e)}")

    @bot.tree.command(name="reload_options", description="Reload LoRA and Resolution options")
    @has_admin_or_bot_manager_role()
    async def reload_options_command(interaction: discord.Interaction):
        try:
            await bot.reload_options()
            await interaction.response.send_message("LoRA and Resolution options have been reloaded.",
                                                  ephemeral=True)
        except Exception as e:
            logger.error(f"Error reloading options: {str(e)}", exc_info=True, stack_info=True)
            await interaction.response.send_message(f"Error reloading options: {str(e)}", ephemeral=True)

    @bot.tree.error
    async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"This command is on cooldown. Try again in {error.retry_after:.2f}s",
                ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "You don't have permission to use this command.",
                ephemeral=True
            )
        else:
            logger.error(f"Command error: {str(error)}", exc_info=True)
            await interaction.response.send_message( 
                f"An error occurred while executing the command: {str(error)}", 
                ephemeral=True
            )

    logger.info("All commands have been set up successfully")