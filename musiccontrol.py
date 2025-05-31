import discord
from discord.ext import commands, tasks
import logging
import wavelink

import datetime

from functools import wraps

from .config import CONFIG

from .ui import create_song_embed, create_queue_embed

class Music(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.vc = None
    self.last_channel = None
    self.skipped = None
    self.last_action = None

    self.leave_if_inactive.start()

  def vc_expected(f):
    @wraps(f)
    async def wrapped(self, ctx, *args, **kwargs):
      if self.vc is None or not self.vc.connected:
        await ctx.respond("To run this the bot must be in a voice channel.")
        return
      else:
        return await f(self, ctx, *args, **kwargs)
    return wrapped
  
  def action(f):
    @wraps(f)
    async def wrapped(self, ctx, *args, **kwargs):
      self.last_action = datetime.datetime.now()
      return await f(self, ctx, *args, **kwargs)
    return wrapped


  @commands.Cog.listener()
  async def on_ready(self):
    await self.connect_nodes()

  @commands.Cog.listener()
  async def on_command_error(self, ctx, err):
    logging.error(err)

  @commands.Cog.listener()
  async def on_wavelink_track_end(self, node):
    if not self.vc.queue.is_empty:
      self.last_action = datetime.datetime.now()
      next_track = self.vc.queue.get()
      await self.vc.play(next_track)

      #check if the song ended or if someone ran skip command
      if self.skipped is not None:
        await self.skipped.respond(embed=create_song_embed(next_track))
        self.skipped = None
      else:
        await self.bot.get_channel(self.last_channel).send(embed=create_song_embed(next_track))

  async def connect_nodes(self):
    await self.bot.wait_until_ready()

    logging.info("Connecting to lavalink server.")
    node: wavelink.Node = wavelink.Node(uri=CONFIG.LAVALINK_URI, password=CONFIG.LAVALINK_PASSWORD)
    await wavelink.Pool.connect(client=self.bot, nodes=[node])
    logging.info("Lavalink connected and ready!")

  @tasks.loop(minutes = 1)
  async def leave_if_inactive(self):
    if self.last_action is None:
      return
    
    if self.vc is None or self.vc.playing:
      return
    
    now = datetime.datetime.now()
    diff = now - self.last_action

    TIMEOUT = datetime.timedelta(minutes=15)
    if diff > TIMEOUT:
      await self.vc.disconnect()
      self.vc = None
      self.last_action = None

      if self.last_channel is not None:
        await self.bot.get_channel(self.last_channel).send("Bot has been inactive for the last 15 minutes. Leaving channel.")
        



  
  @commands.slash_command(name="np", description="Displays the currently playing song.")
  @vc_expected
  @action
  async def now_playing(self, ctx):
    if not self.vc.playing:
      await ctx.respond("Nothing is playing.")
      return
    song = self.vc.current
    await ctx.respond(embed=create_song_embed(song, player = self.vc))

  @commands.slash_command(name="pause", description="Toggles pausing/playing songs.")
  @vc_expected
  @action
  async def pause(self, ctx):
    if self.vc.paused:
      await self.vc.pause(False)
      await ctx.respond("**Resumed.** :arrow_forward:", embed=create_song_embed(self.vc.current, player = self.vc))
    else:
      await self.vc.pause(True)
      await ctx.respond("**Paused.** :pause_button:")

  @commands.slash_command(name="queue", description="Displays the queue.")
  @vc_expected
  @action
  async def queue(self, ctx):
    await ctx.respond(embed=create_queue_embed(self.vc))

  @commands.slash_command(name="stop", description="Stops the music.")
  @vc_expected
  @action
  async def stop(self, ctx):
    await self.vc.stop()
    await ctx.respond("Stopped.")

  @commands.slash_command(name="skip", description="Skips the playing song.")
  @vc_expected
  @action
  async def skip(self, ctx):
    try:
      self.skipped = ctx
      await self.vc.skip()
    except wavelink.QueueEmpty:
      await self.vc.stop()
      await ctx.respond("The queue is empty, so nothing else will be played.")

  @commands.command(name="leave", description="Tells the bot to leave the voice channel.")
  @vc_expected
  @action
  async def leave(self, ctx, args):
    await self.vc.disconnect()
    self.vc = None


  @commands.slash_command(description="Play a song. Unpauses if paused.")
  @action
  async def play(self, ctx, song_title: discord.Option(str, description="Enter the title or url of the song you want to play.") = None):
    await ctx.defer()

    if self.last_channel is None:
      self.last_channel = ctx.channel.id
    
    # Ensure the bot is in a voice channel
    if not self.vc or not self.vc.connected:
      self.vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)

    if song_title is None:
      await self.pause(ctx)
    
    if ctx.author.voice.channel.id != self.vc.channel.id:
      await ctx.respond("You must be in the same voice channel as the bot.")
      return
    
    logging.debug(f"Searching for {song_title}")
    songs = await wavelink.Playable.search(song_title)
    if not songs:
      await ctx.respond(f"No songs found for {song_title}.")
      return

    song = songs[0]
    self.vc.queue.put(song)
    if self.vc.playing:
      await ctx.respond(embed=create_song_embed(song, title="**Added to Queue**"))
    elif len(self.vc.queue) == 1:
      await self.vc.play(self.vc.queue.get(), volume=30)
      await self.now_playing(ctx)