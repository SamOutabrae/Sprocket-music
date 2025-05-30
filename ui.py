import discord
from discord.ext import commands
import discord.ui as ui
import math, re

import time

def get_youtube_thumbnail_url(youtube_url):
    # Regular expression to extract the video ID from the YouTube URL
    video_id_match = re.search(r'(?:v=|\/)([0-9A-Za-z_-]{11}).*', youtube_url)
    
    if not video_id_match:
        raise ValueError("Invalid YouTube URL")
    
    video_id = video_id_match.group(1)
    thumbnail_url = f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
    
    return thumbnail_url

def to_minutes_seconds(duration):
    total_seconds = duration // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02}"

def create_song_progress(song, player) -> str:
    STRING_LENGTH = 30
    duration = song.length
    position = player.position

    index = math.floor((position*STRING_LENGTH/duration) % STRING_LENGTH)

    comp = ['-' for i in range(STRING_LENGTH)]
    comp[index] = '|'

    return f"`{to_minutes_seconds(position)} {''.join(comp)} {to_minutes_seconds(duration)}`"

def create_song_embed(song, player = None, title="**Now Playing**"):
    seconds = (song.length // 1000) % 60
    minutes = (song.length // (1000 * 60)) % 60
    
    time = f"{minutes}:{seconds:02}"

    progress_string = create_song_progress(song, player) if player is not None else ""

    embed = discord.Embed(title=title, description=f"[{song.title}]({song.uri})\n {progress_string}", color=discord.Color.from_hsv(0.58, 0.51, 1))
    #embed.add_field(name=f"[{song.title}]({song.uri})", value="test")
    embed.set_image(url=get_youtube_thumbnail_url(song.uri))
    return embed

def create_queue_embed(vc):
    length = f"`{vc.current.length // 1000 // 60}:{(vc.current.length // 1000) % 60:02}`"
    body = f"[{vc.current.title}]({vc.current.uri}){length}\n\n"
    for i, song in enumerate(vc.queue):
        length = f"`{song.length // 1000 // 60}:{(song.length // 1000) % 60:02}`"
        body += f"`{i+1}` [{song.title}]({song.uri}){length}\n"

    embed = discord.Embed(title=f"**Music Queue ({len(vc.queue)} tracks) **", color=discord.Color.from_hsv(0.58, 0.51, 1))
    embed.add_field(name="**Now Playing**", value=body)

    return embed