#!/usr/bin/env python3
"""
MIDI Player and Editor Module for IRC Bot
Allows users to create, edit, and play MIDI files via IRC commands
"""

import os
import json
import threading
import time
import logging
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple

@dataclass
class MidiNote:
    """Represents a MIDI note"""
    note: int  # MIDI note number (0-127)
    velocity: int  # Note velocity (0-127)
    start_time: float  # Start time in beats
    duration: float  # Duration in beats
    track: int = 0  # Track number
    
    def __post_init__(self):
        """Validate note parameters"""
        self.note = max(0, min(127, self.note))
        self.velocity = max(0, min(127, self.velocity))
        self.start_time = max(0, self.start_time)
        self.duration = max(0, self.duration)

@dataclass
class MidiTrack:
    """Represents a MIDI track"""
    name: str
    instrument: int = 0  # MIDI program number (0-127)
    notes: List[MidiNote] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []

class MidiComposition:
    """Manages a MIDI composition"""
    
    def __init__(self, name: str = "Untitled", tempo: int = 120):
        self.name = name
        self.tempo = tempo  # BPM
        self.tracks: List[MidiTrack] = [MidiTrack("Track 1")]
        self.time_signature = (4, 4)  # numerator, denominator
        
    def add_note(self, track_idx: int, note: int, velocity: int, 
                 start_time: float, duration: float) -> bool:
        """Add a note to a track"""
        if 0 <= track_idx < len(self.tracks):
            midi_note = MidiNote(note, velocity, start_time, duration, track_idx)
            self.tracks[track_idx].notes.append(midi_note)
            return True
        return False
    
    def remove_note(self, track_idx: int, note_idx: int) -> bool:
        """Remove a note from a track"""
        if 0 <= track_idx < len(self.tracks):
            if 0 <= note_idx < len(self.tracks[track_idx].notes):
                self.tracks[track_idx].notes.pop(note_idx)
                return True
        return False
    
    def add_track(self, name: str = None) -> int:
        """Add a new track and return its index"""
        if name is None:
            name = f"Track {len(self.tracks) + 1}"
        self.tracks.append(MidiTrack(name))
        return len(self.tracks) - 1
    
    def set_instrument(self, track_idx: int, instrument: int) -> bool:
        """Set instrument for a track"""
        if 0 <= track_idx < len(self.tracks):
            self.tracks[track_idx].instrument = max(0, min(127, instrument))
            return True
        return False
    
    def get_duration(self) -> float:
        """Get total composition duration in beats"""
        max_time = 0
        for track in self.tracks:
            for note in track.notes:
                end_time = note.start_time + note.duration
                max_time = max(max_time, end_time)
        return max_time
    
    def to_dict(self) -> dict:
        """Convert composition to dictionary for JSON serialization"""
        return {
            'name': self.name,
            'tempo': self.tempo,
            'time_signature': self.time_signature,
            'tracks': [
                {
                    'name': track.name,
                    'instrument': track.instrument,
                    'notes': [asdict(note) for note in track.notes]
                }
                for track in self.tracks
            ]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'MidiComposition':
        """Create composition from dictionary"""
        comp = cls(data.get('name', 'Untitled'), data.get('tempo', 120))
        comp.time_signature = tuple(data.get('time_signature', [4, 4]))
        comp.tracks = []
        
        for track_data in data.get('tracks', []):
            track = MidiTrack(
                track_data.get('name', 'Track'),
                track_data.get('instrument', 0),
                []
            )
            for note_data in track_data.get('notes', []):
                note = MidiNote(**note_data)
                track.notes.append(note)
            comp.tracks.append(track)
        
        return comp

class SimpleMidiPlayer:
    """Simple MIDI player using system beep/sound (no external dependencies)"""
    
    # Note frequencies for basic playback
    NOTE_FREQS = {
        60: 261.63,  # C4
        61: 277.18,  # C#4
        62: 293.66,  # D4
        63: 311.13,  # D#4
        64: 329.63,  # E4
        65: 349.23,  # F4
        66: 369.99,  # F#4
        67: 392.00,  # G4
        68: 415.30,  # G#4
        69: 440.00,  # A4
        70: 466.16,  # A#4
        71: 493.88,  # B4
        72: 523.25,  # C5
    }
    
    def __init__(self):
        self.playing = False
        self.play_thread = None
        self.logger = logging.getLogger(__name__)
        
    def play_composition(self, composition: MidiComposition):
        """Play a MIDI composition"""
        if self.playing:
            self.logger.warning("Already playing")
            return False
        
        self.playing = True
        self.play_thread = threading.Thread(
            target=self._play_worker,
            args=(composition,),
            daemon=True
        )
        self.play_thread.start()
        return True
    
    def _play_worker(self, composition: MidiComposition):
        """Worker thread for playing composition"""
        try:
            # Calculate beat duration in seconds
            beat_duration = 60.0 / composition.tempo
            
            # Collect all note events
            events = []
            for track in composition.tracks:
                for note in track.notes:
                    # Note on event
                    events.append((note.start_time * beat_duration, 'on', note))
                    # Note off event
                    events.append(((note.start_time + note.duration) * beat_duration, 'off', note))
            
            # Sort by time
            events.sort(key=lambda x: x[0])
            
            start_time = time.time()
            for event_time, event_type, note in events:
                if not self.playing:
                    break
                
                # Wait until event time
                current_time = time.time() - start_time
                wait_time = event_time - current_time
                if wait_time > 0:
                    time.sleep(wait_time)
                
                # Log the note event (can't actually play without audio library)
                if event_type == 'on':
                    note_name = self._note_to_name(note.note)
                    self.logger.info(f"Note ON: {note_name} (MIDI {note.note}) velocity {note.velocity}")
        
        except Exception as e:
            self.logger.error(f"Playback error: {e}")
        finally:
            self.playing = False
    
    def stop(self):
        """Stop playback"""
        self.playing = False
        if self.play_thread:
            self.play_thread.join(timeout=1)
    
    @staticmethod
    def _note_to_name(note_num: int) -> str:
        """Convert MIDI note number to note name"""
        notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (note_num // 12) - 1
        note = notes[note_num % 12]
        return f"{note}{octave}"

class MidiManager:
    """Manages MIDI compositions for multiple users"""
    
    def __init__(self, storage_dir: str = "midi_files"):
        self.storage_dir = storage_dir
        self.compositions: Dict[str, MidiComposition] = {}  # {username: composition}
        self.player = SimpleMidiPlayer()
        self.logger = logging.getLogger(__name__)
        
        # Create storage directory
        os.makedirs(storage_dir, exist_ok=True)
        
    def get_composition(self, username: str) -> MidiComposition:
        """Get or create composition for user"""
        if username not in self.compositions:
            # Try to load from file
            filepath = os.path.join(self.storage_dir, f"{username}.json")
            if os.path.exists(filepath):
                self.load_composition(username)
            else:
                self.compositions[username] = MidiComposition(f"{username}'s composition")
        
        return self.compositions[username]
    
    def save_composition(self, username: str) -> bool:
        """Save user's composition to file"""
        if username not in self.compositions:
            return False
        
        try:
            filepath = os.path.join(self.storage_dir, f"{username}.json")
            with open(filepath, 'w') as f:
                json.dump(self.compositions[username].to_dict(), f, indent=2)
            return True
        except Exception as e:
            self.logger.error(f"Failed to save composition for {username}: {e}")
            return False
    
    def load_composition(self, username: str) -> bool:
        """Load user's composition from file"""
        try:
            filepath = os.path.join(self.storage_dir, f"{username}.json")
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.compositions[username] = MidiComposition.from_dict(data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to load composition for {username}: {e}")
            return False
    
    def list_user_files(self, username: str) -> List[str]:
        """List saved compositions for a user"""
        files = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith(username) and filename.endswith('.json'):
                files.append(filename[:-5])  # Remove .json extension
        return files
    
    def play(self, username: str) -> bool:
        """Play user's composition"""
        if username not in self.compositions:
            return False
        return self.player.play_composition(self.compositions[username])
    
    def stop(self):
        """Stop playback"""
        self.player.stop()
    
    def format_composition_info(self, username: str) -> str:
        """Format composition info for display"""
        if username not in self.compositions:
            return f"No composition found for {username}"
        
        comp = self.compositions[username]
        info = [
            f"🎵 {comp.name}",
            f"Tempo: {comp.tempo} BPM",
            f"Time Signature: {comp.time_signature[0]}/{comp.time_signature[1]}",
            f"Duration: {comp.get_duration():.1f} beats",
            f"Tracks: {len(comp.tracks)}"
        ]
        
        for i, track in enumerate(comp.tracks):
            info.append(f"  Track {i}: {track.name} ({len(track.notes)} notes, instrument {track.instrument})")
        
        return " | ".join(info)
