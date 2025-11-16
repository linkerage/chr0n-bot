# MIDI Editor Quick Reference Guide

## Overview
The IRC bot now supports collaborative MIDI composition! Each user can create and edit their own musical compositions directly from IRC.

## Basic Commands

### Getting Help
```
!midi
```
Shows available MIDI commands

### View Your Composition
```
!midi info
```
Displays your current composition details (tempo, tracks, notes, duration)

### Play Your Composition
```
!midi play
```
Plays your composition. Note events are logged to the bot's log file.

### Stop Playback
```
!midi stop
```
Stops the currently playing composition

## Editing Commands

### Add a Note
```
!midi add <track> <note> <velocity> <start> <duration>
```
- **track**: Track number (0, 1, 2, etc.)
- **note**: MIDI note number (0-127, middle C = 60)
- **velocity**: How loud (0-127, typically use 80-100)
- **start**: Start time in beats (0, 0.5, 1, 2, etc.)
- **duration**: Length in beats (0.25, 0.5, 1, 2, etc.)

**Example:** `!midi add 0 60 100 0 1` - Add middle C on track 0 at beat 0 for 1 beat

### Set Tempo
```
!midi tempo <bpm>
```
Sets beats per minute (20-300)

**Example:** `!midi tempo 140` - Set tempo to 140 BPM

### Add a Track
```
!midi track <name>
```
Adds a new track to your composition

**Example:** `!midi track Bass` - Add a track named "Bass"

### Set Track Instrument
```
!midi instrument <track> <instrument_number>
```
Sets the MIDI instrument for a track (0-127)

**Example:** `!midi instrument 0 33` - Set track 0 to acoustic bass

### Save Your Work
```
!midi save
```
Saves your composition to disk (auto-saves after most edits)

### Clear Composition
```
!midi clear
```
Deletes all notes and starts fresh

## MIDI Note Numbers Reference

| Note | Number | Note | Number | Note | Number |
|------|--------|------|--------|------|--------|
| C3   | 48     | C4   | 60     | C5   | 72     |
| C#3  | 49     | C#4  | 61     | C#5  | 73     |
| D3   | 50     | D4   | 62     | D5   | 74     |
| D#3  | 51     | D#4  | 63     | D#5  | 75     |
| E3   | 52     | E4   | 64     | E5   | 76     |
| F3   | 53     | F4   | 65     | F5   | 77     |
| F#3  | 54     | F#4  | 66     | F#5  | 78     |
| G3   | 55     | G4   | 67     | G5   | 79     |
| G#3  | 56     | G#4  | 68     | G#5  | 80     |
| A3   | 57     | A4   | 69     | A5   | 81     |
| A#3  | 58     | A#4  | 70     | A#5  | 82     |
| B3   | 59     | B4   | 71     | B5   | 83     |

Middle C is **C4 = 60**

## Common MIDI Instruments

| Number | Instrument           |
|--------|---------------------|
| 0      | Acoustic Grand Piano |
| 24     | Acoustic Guitar     |
| 33     | Acoustic Bass       |
| 40     | Violin              |
| 56     | Trumpet             |
| 65     | Alto Sax            |
| 73     | Flute               |
| 80     | Square Lead (synth) |

[Full GM MIDI instrument list](https://en.wikipedia.org/wiki/General_MIDI#Program_change_events)

## Example: Creating a Simple Melody

```irc
!midi clear                          # Start fresh
!midi tempo 120                      # Set to 120 BPM
!midi add 0 60 100 0 1              # C
!midi add 0 62 100 1 1              # D
!midi add 0 64 100 2 1              # E
!midi add 0 65 100 3 1              # F
!midi add 0 67 100 4 2              # G (held for 2 beats)
!midi info                           # Check your work
!midi play                           # Play it!
```

## Example: Adding a Bass Track

```irc
!midi track Bass                     # Add new track (becomes track 1)
!midi instrument 1 33                # Set to acoustic bass
!midi add 1 48 80 0 4               # Low C for 4 beats
!midi add 1 53 80 4 4               # F for 4 beats
!midi play                           # Play both tracks
```

## Tips

1. **Start Simple**: Begin with one track and a few notes
2. **Beat Timing**: Use 0, 0.25, 0.5, 0.75, 1.0, etc. for rhythms
3. **Velocity**: 80-100 is a good range for most notes
4. **Auto-Save**: Most commands auto-save, but `!midi save` is available
5. **Overlapping Notes**: You can add notes that play simultaneously
6. **Duration**: Note duration affects when the note stops playing

## Files

Your compositions are saved in: `midi_files/<your_nick>.json`

Each user has their own composition that persists between sessions!
