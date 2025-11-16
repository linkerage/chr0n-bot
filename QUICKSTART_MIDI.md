# MIDI Editor Quick Start

## Try It Right Now!

### On IRC
Connect to your IRC bot's channel and try these commands:

```
!midi
!midi clear
!midi add 0 60 100 0 1
!midi add 0 64 100 1 1
!midi add 0 67 100 2 1
!midi info
!midi play
```

You just created a C-E-G chord progression!

### Test Locally (Without IRC)

```bash
cd /home/oem/chr0n-bot
python3 << 'EOF'
from midi_player import MidiManager

# Create manager
m = MidiManager()

# Create a simple melody
comp = m.get_composition('demo_user')
comp.tempo = 120

# Add notes (Middle C scale: C D E F G)
comp.add_note(0, 60, 100, 0, 1)    # C
comp.add_note(0, 62, 100, 1, 1)    # D
comp.add_note(0, 64, 100, 2, 1)    # E
comp.add_note(0, 65, 100, 3, 1)    # F
comp.add_note(0, 67, 100, 4, 1)    # G

# Save it
m.save_composition('demo_user')

# Show info
print(m.format_composition_info('demo_user'))

# Play it (notes will be logged)
import time
m.play('demo_user')
time.sleep(6)  # Wait for playback
m.stop()

print("\nDone! Check midi_files/demo_user.json")
EOF
```

## Common Patterns

### Simple Melody
```
!midi clear
!midi tempo 120
!midi add 0 60 100 0 1
!midi add 0 62 100 1 1
!midi add 0 64 100 2 1
!midi play
```

### Chord (Notes at Same Time)
```
!midi clear
!midi add 0 60 100 0 2
!midi add 0 64 100 0 2
!midi add 0 67 100 0 2
!midi play
```

### Two Tracks (Melody + Bass)
```
!midi clear
!midi add 0 67 100 0 1
!midi add 0 69 100 1 1
!midi track Bass
!midi instrument 1 33
!midi add 1 43 80 0 2
!midi play
```

### Fast Notes (16th notes at 120 BPM)
```
!midi clear
!midi tempo 120
!midi add 0 60 100 0 0.25
!midi add 0 62 100 0.25 0.25
!midi add 0 64 100 0.5 0.25
!midi add 0 65 100 0.75 0.25
!midi play
```

## Understanding the Numbers

### `!midi add <track> <note> <velocity> <start> <duration>`

- **track**: 0 = first track, 1 = second, etc.
- **note**: 60 = middle C, 61 = C#, 62 = D, etc.
- **velocity**: 100 = loud, 80 = medium, 60 = soft
- **start**: 0 = beginning, 1 = 1 beat later, 0.5 = half beat
- **duration**: 1 = whole beat, 0.5 = half beat, 2 = two beats

## Useful MIDI Note Numbers

Quick reference for common notes:

```
C3=48  C4=60  C5=72
D3=50  D4=62  D5=74
E3=52  E4=64  E5=76
F3=53  F4=65  F5=77
G3=55  G4=67  G5=79
A3=57  A4=69  A5=81
B3=59  B4=71  B5=83
```

Middle C = 60

## Next Steps

1. See `MIDI_GUIDE.md` for full documentation
2. See `MIDI_EXAMPLE_SESSION.txt` for example IRC sessions
3. See `MIDI_IMPLEMENTATION.md` for technical details
4. Your compositions are saved in `midi_files/<your_username>.json`

## Troubleshooting

**Bot doesn't respond to !midi**
- Make sure bot is running: `./ircbot.py`
- Check bot is in your channel
- Try `!ping` first to test bot is alive

**No sound when playing**
- This is normal! Currently only logs notes
- Check `ircbot.log` to see note events
- Future version could add real audio

**Lost my composition**
- Check `midi_files/` directory
- Files are named `<username>.json`
- You can edit JSON files directly if needed

**Made a mistake**
- Use `!midi clear` to start over
- Or stop bot and delete your JSON file

Have fun making music on IRC! 🎵
