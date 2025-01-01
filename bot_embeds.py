from discord import Embed, Role

def add_song(name: str, author: str, queue_pos: int):
    r_embed = Embed(color=0x2ebd3f, title="Added song 🎵")
    r_embed.description = f"```\'{name}\' by {author}```\n**Position in queue: {queue_pos}**"

    return r_embed

def now_playing(name: str, author: str):
    r_embed = Embed(color=0x2ebd3f, title="Now playing 🎶")
    r_embed.description = f"```\'{name}\' by {author}```"

    return r_embed

def song_stopped():
    return Embed(color=0xb90505, title="Song stopped", description="Run **/play** or **/search** to listen to more music")

def no_song():
    return Embed(color=0xb90505, title="No song", description="You have to be listening to a song to use this command")

def no_songs_queue():
    return Embed(color=0xb90505, title="No songs", description="No songs in queue, use **/play** to add more")

def skipped_song(songs_left: int):
    return Embed(color=0x16acac, title="Skipped song", description=f"The current song has been skipped, **Songs left in queue: {songs_left}**")

def not_view_owner():
    return Embed(color=0x16acac, title="Invalid permissions", description="You are not the view owner or you lack sufficient permissions to interact with it")

def already_paused():
    return Embed(color=0xb90505, title="Song already paused", description="The song is already paused")

def already_playing():
    return Embed(color=0xb90505, title="Song already playing", description="The song is already playing")

def paused():
    return Embed(color=0xb90505, title="Song paused")

def resumed():
    return Embed(color=0xb90505, title="Song resumed")

def queue_updated():
    return Embed(color=0x2ebd3f, title="Queue updated")

def song_added():
    return Embed(color=0x2ebd3f, title="Song added")

def not_admin():
    return Embed(color=0xb90505, title="Invalid permissions", description="You are not an administrator of this server")

def music_role_set(role: Role):
    return Embed(color=0x2ebd3f, title="Music role set", description=f"Music role set to {role.mention}")

def no_search_results():
    return Embed(color=0xb90505, title="No search results", description="No results found for the search query")

def command_not_found():
    return Embed(color=0xb90505, title="Command not found", description="The command you entered does not exist")