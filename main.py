import discord
from discord.ext import commands
from discord import app_commands
import externals
import asyncio
import pytubefix
import io
import config
from config import logging
from queue import Queue
import threading
import bot_embeds
import db_handler
import os

song_buffer: dict[str, io.BytesIO] = {}
guild_music_roles: dict[int, discord.Role] = {} # guild_id: discord.Role

logger = logging.getLogger('discord')

class Song():
    def __init__(self, youtube_link: str):
        if youtube_link in song_buffer:
            self.__song_bytes = song_buffer[youtube_link]
            logger.info("Loaded song from memory")
        else:
            yt = pytubefix.YouTube(youtube_link)
            audio_stream = yt.streams.filter(only_audio=True).first()

            audio_buffer = io.BytesIO()

            audio_stream.stream_to_buffer(audio_buffer)
            audio_buffer.seek(0)

            self.__song_bytes = audio_buffer
            song_buffer[youtube_link] = audio_buffer
            logger.info("Loaded song from remote address")

        self.yt = pytubefix.YouTube(youtube_link)

    def get_bytes(self):
        return io.BytesIO(self.__song_bytes.getvalue())


class GuildMusicQueue():
    def __init__(self, guild: discord.Guild, voiceClient: discord.VoiceClient = None, default_channel: discord.VoiceChannel = None):
        self.guild = guild
        self.voiceClient = voiceClient
        self.defaultChannel = default_channel

        self.queue = Queue()
        self.main_message: discord.WebhookMessage = None
        self.main_message_owner: discord.Member = None

    async def join_voice_channel(self, channel: discord.VoiceChannel = None) -> bool:
        if self.voiceClient and self.voiceClient.is_connected():
            return True
        
        if channel is None:
            self.voiceClient = await self.defaultChannel.connect(self_deaf=True)
            return False

        if channel:
            self.voiceClient = await channel.connect(self_deaf=True)
            return False
        
        logger.error(f"No default channel or channel specified for {self.guild.name}")

    def pause(self):
        if not self.voiceClient.is_paused():
            self.voiceClient.pause()

    def resume(self):
        if self.voiceClient.is_paused():
            self.voiceClient.resume()

    def skip(self):
        if self.voiceClient:
            self.voiceClient.stop()

    def add_song(self, song: Song):
        self.queue.put(song)

    def get_next_song(self) -> Song | None:
        if not self.queue.empty():
            return self.queue.get()
        return None
    
    def start_next(self, error = None):
        song = self.get_next_song()
        if song:
            logger.info(f"Found next song {song.yt.title}")
            asyncio.run_coroutine_threadsafe(self.play_song(song), bot.loop)
            if self.main_message:
                asyncio.run_coroutine_threadsafe(self.main_message.edit(embed=bot_embeds.now_playing(song.yt.title, song.yt.author)), bot.loop)
        else:
            if self.voiceClient:
                asyncio.run_coroutine_threadsafe(self.play_song(song), bot.loop)
                asyncio.run_coroutine_threadsafe(self.voiceClient.disconnect(), bot.loop)
    
    async def play_song(self, song: Song):
        if not song:
            await self.main_message.edit(embed=bot_embeds.song_stopped(), view=None)
            return
        
        await self.join_voice_channel()

        audio_buffer = song.get_bytes()

        audio_source = discord.FFmpegPCMAudio(
            audio_buffer,
            pipe=True
        )

        self.voiceClient.play(audio_source, after=self.start_next)

    def is_playing_song(self) -> bool:
        if self.voiceClient and self.voiceClient.is_connected():
            if self.voiceClient.is_playing():
                return True

        return False

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='/', intents=intents)

music_queues: dict[int, GuildMusicQueue] = {}

class MusicView(discord.ui.View):
    def __init__(self, music_queue: GuildMusicQueue, view_owner: discord.Member):
        super().__init__(timeout=None)
        self.m_queue = music_queue
        self.view_owner = view_owner

        music_queue.main_message_owner = view_owner

    def can_use_view(self, user: discord.Member):
        if user.guild_permissions.administrator:
            return True
        elif user.id == self.view_owner.id:
            return True
        
        return False

    @discord.ui.button(label="⏩ Skip", style=discord.ButtonStyle.blurple)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_use_view(interaction.user):
            await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
            return

        if not self.m_queue.is_playing_song():
            await interaction.response.send_message(embed=bot_embeds.no_song(), ephemeral=True)
            return
        
        songs = self.m_queue.queue.qsize()

        self.m_queue.skip()

        await interaction.response.send_message(embed=bot_embeds.skipped_song(songs - 1), ephemeral=True)

    @discord.ui.button(label="🛑 Stop", style=discord.ButtonStyle.danger)
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_use_view(interaction.user):
            await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
            return

        if not self.m_queue.is_playing_song():
            await interaction.response.send_message(embed=bot_embeds.no_song(), ephemeral=True)
            return
        
        if self.m_queue.voiceClient:
            asyncio.create_task(self.m_queue.voiceClient.disconnect())
            self.m_queue.voiceClient.stop()

        if self.m_queue.main_message:
            await self.m_queue.main_message.edit(embed=bot_embeds.song_stopped(), view=None)
        await interaction.response.send_message(embed=bot_embeds.song_stopped(), ephemeral=True)
        self.m_queue.main_message = None
        self.m_queue.main_message_owner = None

    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.green)
    async def pause(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_use_view(interaction.user):
            await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
            return
        
        if not self.m_queue.is_playing_song():
            await interaction.response.send_message(embed=bot_embeds.no_song(), ephemeral=True)
            return
        
        if self.m_queue.voiceClient.is_paused():
            await interaction.response.send_message(embed=bot_embeds.already_paused(), ephemeral=True)
            return
        
        self.m_queue.pause()
        await interaction.response.send_message(embed=bot_embeds.paused(), ephemeral=True)

    @discord.ui.button(label="▶️ Resume", style=discord.ButtonStyle.green)
    async def resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.can_use_view(interaction.user):
            await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
            return
        
        if not self.m_queue.voiceClient.is_paused():
            await interaction.response.send_message(embed=bot_embeds.already_playing(), ephemeral=True)
            return
        
        self.m_queue.resume()
        await interaction.response.send_message(embed=bot_embeds.resumed(), ephemeral=True)


async def can_use_command(member: discord.Member):
    if member.guild_permissions.administrator:
        return True
    
    if m_queue := music_queues.get(member.guild.id):
        if m_queue and m_queue.main_message_owner:
            if m_queue.main_message_owner.id == member.id:
                return True
            return False

    if role := guild_music_roles.get(member.guild.id):
        if role in member.roles:
            return True

    return False

@bot.event
async def on_ready():
    logger.info("Gang we locked and loaded")
    try:
        await bot.tree.sync()
    except Exception as e:
        print(e)
        pass

    for guild in bot.guilds:
        guild_music_roles[guild.id] = db_handler.get_music_role(bot, guild.id)

@bot.tree.command(name="play", description="Play a youtube video")
async def play(interaction: discord.Interaction, video: str, channel: discord.VoiceChannel):
    m_queue = music_queues.setdefault(interaction.guild.id, GuildMusicQueue(interaction.guild, None, channel))

    if not await can_use_command(interaction.user):
        await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
        return

    if m_queue.queue.qsize() < 1 and not m_queue.is_playing_song():
        song = Song(video)
        m_queue.add_song(song)
    else:
        song = Song(video)
        m_queue.add_song(song)
        q_pos = m_queue.queue.qsize()
        await m_queue.main_message.edit(embed=bot_embeds.add_song(song.yt.title, song.yt.author, q_pos))
        await interaction.response.send_message(embed=bot_embeds.song_added(), ephemeral=True)
        return

    await interaction.response.defer()

    play_thread = threading.Thread(target=m_queue.start_next)
    play_thread.start()
    
    m_queue.main_message = await interaction.followup.send(embed=bot_embeds.now_playing(song.yt.title, song.yt.author), view=MusicView(m_queue, interaction.user))

# use pytubefix Search to find videos and play the first one
@bot.tree.command(name="search", description="Search youtube for a video to play")
async def search(interaction: discord.Interaction, query: str, channel: discord.VoiceChannel = None):
    m_queue = music_queues.setdefault(interaction.guild.id, GuildMusicQueue(interaction.guild, None, channel))

    if not await can_use_command(interaction.user):
        await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
        return

    # search
    search_results = pytubefix.Search(query)
    if not search_results:
        await interaction.response.send_message(embed=bot_embeds.no_search_results(), ephemeral=True)
        return
    
    # get first result
    video = search_results.videos[0]

    if not channel and not m_queue.defaultChannel:
        await interaction.response.send_message(embed=bot_embeds.no_song(), ephemeral=True)
        return
    
    channel = m_queue.defaultChannel or channel

    if m_queue.queue.qsize() < 1 and not m_queue.is_playing_song():
        song = Song(video.watch_url)
        m_queue.add_song(song)
    else:
        song = Song(video.watch_url)
        m_queue.add_song(song)
        q_pos = m_queue.queue.qsize()
        await m_queue.main_message.edit(embed=bot_embeds.add_song(song.yt.title, song.yt.author, q_pos))
        await interaction.response.send_message(embed=bot_embeds.song_added(), ephemeral=True)
        return
    
    await interaction.response.defer()

    play_thread = threading.Thread(target=m_queue.start_next)
    play_thread.start()

    m_queue.main_message = await interaction.followup.send(embed=bot_embeds.now_playing(song.yt.title, song.yt.author), view=MusicView(m_queue, interaction.user))

@bot.tree.command(name="skip", description="Skip the current song")
async def skip(interaction: discord.Interaction):
    if interaction.guild.id not in music_queues:
        await interaction.response.send_message(embed=bot_embeds.no_song())
        return
    m_queue = music_queues[interaction.guild.id]

    if not await can_use_command(interaction.user):
        await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
        return

    songs = m_queue.queue.qsize()

    m_queue.skip()
    await interaction.response.send_message(embed=bot_embeds.skipped_song(songs - 1))

@bot.tree.command(name="stop", description="Stop playing songs")
async def stop(interaction: discord.Interaction):
    await interaction.response.defer()
    if not interaction.guild.id not in music_queues:
        await interaction.followup.send(embed=bot_embeds.no_song())
        return
    m_queue = music_queues[interaction.guild.id]

    if await can_use_command(interaction.user):
        await interaction.response.send_message(embed=bot_embeds.not_view_owner(), ephemeral=True)
        return
    
    if m_queue.voiceClient:
        asyncio.create_task(m_queue.voiceClient.disconnect())
        m_queue.voiceClient.stop()

    if m_queue.main_message:
            await m_queue.main_message.edit(embed=bot_embeds.song_stopped(), view=None)
            m_queue.main_message = None
            m_queue.main_message_owner = None
    await interaction.followup.send(embed=bot_embeds.song_stopped())

@bot.tree.command(name="queue", description="Look at the current song queue")
async def queue(interaction: discord.Interaction):
    if interaction.guild.id not in music_queues:
        await interaction.response.send_message(embed=bot_embeds.no_songs_queue(), ephemeral=True)
        return
    m_queue = music_queues[interaction.guild.id]

    if m_queue.queue.qsize() < 1:
        await interaction.response.send_message(embed=bot_embeds.no_songs_queue(), ephemeral=True)
        return

    r_embed = discord.Embed(color=0xffeb00, title=f"Queue ({m_queue.queue.qsize()} Songs)")
    r_embed.description = '**Next song will be played after the current one finishes**'
    item: Song
    for i, item in enumerate(list(m_queue.queue.queue)):
        r_embed.description += f"```{i + 1}. {item.yt.title}```"

    if m_queue.main_message and m_queue.main_message_owner.id == interaction.user.id:
        await m_queue.main_message.edit(embed=r_embed)
        await interaction.response.send_message(embed=bot_embeds.queue_updated(), ephemeral=True)
    else:
        await interaction.response.send_message(embed=r_embed, ephemeral=True)

@bot.tree.command(name="musicrole", description="Set a role that can control the music bot")
async def musicrole(interaction: discord.Interaction, role: discord.Role):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message(embed=bot_embeds.not_admin(), ephemeral=True)
        return

    db_handler.set_music_role(bot, interaction.guild, role)
    guild_music_roles[interaction.guild.id] = role
    await interaction.response.send_message(embed=bot_embeds.music_role_set(role))

@bot.tree.command(name="whatrole", description="Check the current music role")
async def whatrole(interaction: discord.Interaction):
    if role := guild_music_roles.get(interaction.guild.id):
        await interaction.response.send_message(embed=bot_embeds.music_role_set(role))
    else:
        await interaction.response.send_message(embed=bot_embeds.no_songs_queue(), ephemeral=True)

if __name__ == '__main__':
    bot.run(externals.BOT_TOKEN)