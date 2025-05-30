from dataclasses import dataclass

@dataclass
class Config():
  LAVALINK_URI = 'http://localhost:2333'
  LAVALINK_PASSWORD = 'youshallnotpass'

CONFIG = Config()