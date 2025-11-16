# Chronibit (chr0n-bot)

A feature-rich Python IRC bot with cannabis-themed commands, timezone support, games, music composition, and toke tracking.

## 🌿 Key Features

- **🌍 Timezone Support**: Set your location with `!bud-zone` for personalized time-based features
- **🥧 Pi Collection Game**: Collect base64 pi digits at 3:14 AM/PM daily
- **🎲 Craps Game**: Play dice with betting, hot streaks, and comebacks
- **🎵 MIDI Music Editor**: Collaborative music creation via IRC commands
- **🌿 Cannabis Strain Database**: 150+ strains with effects and flavors
- **📊 Toke Analytics**: Track usage, abstinence records, and T-breaks
- **🔥 Philosophical Quotes**: Deep thoughts on combustion and consciousness
- **⏰ Smart Time Features**: Countdown timers and timezone-aware commands

## Commands

### 🌍 Timezone & Location
- `!bud-zone` - Show your current timezone
- `!bud-zone <location>` - Set timezone (e.g., "Los Angeles CA", "London UK")

### 🥧 Pi Collection Game
- `!pi` - Collect 60 base64 pi digits (only at 3:14 AM/PM in your timezone)
- `!pi-show` - Display all your collected pi digits
- Goal: Collect 420 digits to win a round!

### 🎲 Craps Dice Game
- `!craps bet <amount>` - Place a bet and start a new game
- `!craps roll` - Roll the dice
- `!craps status` - Check your bankroll and stats
- `!craps cashout` - Cash out and see final statistics

### 🌿 Cannabis Features
- `!strain <name>` - Get info on 150+ cannabis strains
- `!stoned` - Poetic reflections on elevated consciousness
- `!blaze` - Track toke with philosophical wisdom
- `!edible` - Wisdom about edibles
- `!toke`, `!joint`, `!dab`, `!blunt`, `!bong`, `!vape`, `!pass` - Track toke silently

### 📊 Toke Analytics
- `!z6` - Time since last toke with rank system
- `!t-break` - Show your longest tolerance break

### ⏰ Time Features
- `!time` - Countdown to special date

### 🎵 MIDI Music Editor
- `!midi` - Show MIDI commands
- `!midi info` - View your composition
- `!midi add <track> <note> <velocity> <start> <duration>` - Add a note
- `!midi play` - Play your composition
- `!midi stop` - Stop playback
- `!midi tempo <bpm>` - Set tempo (20-300 BPM)
- `!midi track <name>` - Add a new track
- `!midi instrument <track> <num>` - Set track instrument
- `!midi save` - Save composition
- `!midi clear` - Start fresh
- See **MIDI_GUIDE.md** for complete documentation

### ℹ️ Help
- `!?` - Show all commands in one line

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