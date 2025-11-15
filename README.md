# Chronibit

A Python IRC bot for #gentoo-weed on irc.libera.chat with cannabis-themed commands and toke tracking.

## Features

- **Toke Tracking**: Track time since last toke with `!churchbong` command
- **420 Facts**: Get random cannabis facts with `!churchbong 420`
- **Silent Tracking**: Commands like `!toke`, `!pass`, `!joint`, `!dab`, `!blunt` silently track usage
- **MIDI Music Editor**: Create and edit music collaboratively via IRC with `!midi` commands
- **Gentoo Love**: Random Gentoo-themed responses with `!gentoo`
- **Standard Bot Commands**: `!help`, `!ping`, `!about`, `!uptime`

## Commands

- `!help` - Show available commands
- `!ping` - Pong response
- `!about` - Bot information
- `!uptime` - Show bot uptime
- `!gentoo` - Random Gentoo-themed message
- `!time` - Countdown to December 4th, 2025
- `!churchbong` - Show time since last toked
- `!churchbong 420` - Same as above plus a random 420 fact
- `!toke`, `!pass`, `!joint`, `!dab`, `!blunt`, `!bong`, `!vape`, `!doombong`, `!olddoombong`, `!kylebong` - Silent toke tracking
- `!blaze` - Track toke with motivational message
- `!midi` - MIDI music editor (see MIDI_GUIDE.md for full details)
  - `!midi info` - View your composition
  - `!midi add <track> <note> <velocity> <start> <duration>` - Add a note
  - `!midi play` - Play your composition
  - `!midi stop` - Stop playback
  - `!midi tempo <bpm>` - Set tempo
  - `!midi track <name>` - Add a track
  - `!midi save` - Save composition
  - `!midi clear` - Start fresh

## Setup

1. Install Python 3
2. Create a `config.json` file (optional - bot will create default):

```json
{
  "server": "irc.libera.chat",
  "port": 6667,
  "nickname": "Chr0n-bot",
  "username": "Chr0n-bot", 
  "realname": "Chr0n-bot",
  "channels": ["#gentoo-weed"],
  "command_prefix": "!"
}
```

3. Run the bot:
```bash
python3 ircbot.py
```

## Files

- `ircbot.py` - Main bot code
- `midi_player.py` - MIDI composition and playback module
- `config.json` - Configuration (auto-created if missing)
- `toke_data.pkl` - Persistent toke tracking data
- `ircbot.log` - Bot logs
- `midi_files/` - User MIDI compositions (JSON format)
- `MIDI_GUIDE.md` - Comprehensive MIDI editor guide

## Requirements

- Python 3.x
- Standard library only (no external dependencies)

Blaze on! 🔔💨