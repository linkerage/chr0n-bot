#!/usr/bin/env python3
"""
IRC Bot for #gentoo-weed on irc.libera.chat
"""

import socket
import time
import threading
import json
import os
import logging
import pickle
from datetime import datetime
import pytz
from zoneinfo import ZoneInfo
import base64
from collections import defaultdict
from midi_player import MidiManager

class IRCBot:
    def __init__(self, config_file="config.json"):
        self.load_config(config_file)
        self.socket = None
        self.connected = False
        self.setup_logging()
        self.load_toke_data()
        self.active_420_windows = {}  # {nick: timestamp_when_420_started}
        self.timezone_check_thread = None
        self.midi_manager = MidiManager()
        self.craps_games = {}  # {nick: {'point': None, 'chips': 100, 'bet': 0, 'wins': 0, 'losses': 0}}
        
    def load_config(self, config_file):
        """Load bot configuration from JSON file"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except FileNotFoundError:
            # Use default config if file doesn't exist
            config = {
                "server": "irc.libera.chat",
                "port": 6667,
                "nickname": "Chronibit",
                "username": "Chronibit",
                "realname": "Chronibit",
                "channels": [],
                "command_prefix": "!"
            }
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
        self.server = config["server"]
        self.port = config["port"]
        self.nickname = config["nickname"]
        self.username = config["username"]
        self.realname = config["realname"]
        self.channels = config["channels"]
        self.command_prefix = config["command_prefix"]
        self.nickserv_password = config.get("nickserv_password", None)
        self.nickserv_email = config.get("nickserv_email", None)
        self.nickserv_register = config.get("nickserv_register", False)
        self.nickserv_registered = False
        
    def setup_logging(self):
        """Setup logging for the bot"""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ircbot.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_toke_data(self):
        """Load toke break data from file"""
        self.toke_file = 'toke_data.pkl'
        try:
            with open(self.toke_file, 'rb') as f:
                data = pickle.load(f)
                if isinstance(data, dict) and 'timestamps' in data:
                    self.toke_data = data['timestamps']
                    self.tb_enabled = data.get('tb_enabled', {})
                    self.toke_counts = data.get('toke_counts', {})
                    self.longest_abstinence = data.get('longest_abstinence', {})
                    self.user_timezones = data.get('user_timezones', {})
                    self.precision_timing = data.get('precision_timing', {})
                    self.pi_progress = data.get('pi_progress', {})
                    self.pi_rounds_won = data.get('pi_rounds_won', {})
                    self.timezone_points = data.get('timezone_points', {})
                    self.toke_history = data.get('toke_history', {})
                    self.time_format_mode = data.get('time_format_mode', 0)
                    self.auto_420_points = data.get('auto_420_points', {})  # Points from being at 4:20
                    self.craps_games = data.get('craps_games', {})
                else:
                    # Old format, migrate
                    self.toke_data = data
                    self.tb_enabled = {}
                    self.toke_counts = {}
                    self.longest_abstinence = {}
                    self.user_timezones = {}
                    self.precision_timing = {}
                    self.pi_progress = {}
                    self.pi_rounds_won = {}
                    self.timezone_points = {}
                    self.toke_history = {}
        except (FileNotFoundError, EOFError):
            self.toke_data = {}  # {user: last_toke_timestamp}
            self.tb_enabled = {}  # {user: True/False}
            self.toke_counts = {}  # {user: total_tokes}
            self.longest_abstinence = {}  # {user: longest_seconds}
            self.user_timezones = {}  # {user: timezone_string}
            self.precision_timing = {}  # {user: {'last_420_time': timestamp, 'perfect_cycles': int, 'total_420s': int, 'best_precision': seconds_off}}
            self.pi_progress = {}  # {user: digits_collected}
            self.pi_rounds_won = {}  # {user: rounds_won}
            self.timezone_points = {}  # {user: points_for_guessing_420_times}
            self.toke_history = {}  # {user: [list of timestamps]}
            self.time_format_mode = 0  # 0 = detailed, 1 = seconds
            self.auto_420_points = {}  # Points from being at 4:20
            self.craps_games = {}
            
    def save_toke_data(self):
        """Save toke break data to file"""
        try:
            with open(self.toke_file, 'wb') as f:
                data = {
                    'timestamps': self.toke_data,
                    'tb_enabled': self.tb_enabled,
                    'toke_counts': self.toke_counts,
                    'longest_abstinence': self.longest_abstinence,
                    'user_timezones': self.user_timezones,
                    'precision_timing': self.precision_timing,
                    'pi_progress': self.pi_progress,
                    'pi_rounds_won': self.pi_rounds_won,
                    'timezone_points': self.timezone_points,
                    'toke_history': self.toke_history,
                    'time_format_mode': self.time_format_mode,
                    'auto_420_points': self.auto_420_points,
                    'craps_games': self.craps_games
                }
                pickle.dump(data, f)
        except Exception as e:
            self.logger.error(f"Failed to save toke data: {e}")
            
    def get_abstinence_rating(self, seconds_abstinent):
        """Calculate abstinence rating and breakdown from seconds"""
        # Calculate all time units
        years = int(seconds_abstinent // (365.25 * 24 * 3600))
        remaining = int(seconds_abstinent % (365.25 * 24 * 3600))
        
        months = int(remaining // (30.44 * 24 * 3600))
        remaining = int(remaining % (30.44 * 24 * 3600))
        
        weeks = remaining // (7 * 24 * 3600)
        remaining = remaining % (7 * 24 * 3600)
        
        days = remaining // (24 * 3600)
        remaining = remaining % (24 * 3600)
        
        hours = remaining // 3600
        remaining = remaining % 3600
        
        minutes = remaining // 60
        seconds = remaining % 60
        
        # Build time breakdown with all units, but only add emoji to highest unit
        time_parts = []
        highest_unit_found = False
        
        if years > 0:
            decades = years // 10
            remaining_years = years % 10
            if decades > 0:
                if not highest_unit_found:
                    time_parts.append(f"{decades} decade{'s' if decades != 1 else ''} 👑🏆")
                    highest_unit_found = True
                else:
                    time_parts.append(f"{decades} decade{'s' if decades != 1 else ''}")
            if remaining_years > 0:
                if not highest_unit_found:
                    time_parts.append(f"{remaining_years} year{'s' if remaining_years != 1 else ''} 🏆")
                    highest_unit_found = True
                else:
                    time_parts.append(f"{remaining_years} year{'s' if remaining_years != 1 else ''}")
        if months > 0:
            if not highest_unit_found:
                time_parts.append(f"{months} month{'s' if months != 1 else ''} 🥇")
                highest_unit_found = True
            else:
                time_parts.append(f"{months} month{'s' if months != 1 else ''}")
        if weeks > 0:
            if not highest_unit_found:
                time_parts.append(f"{weeks} week{'s' if weeks != 1 else ''} 🥈")
                highest_unit_found = True
            else:
                time_parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
        if days > 0:
            if not highest_unit_found:
                time_parts.append(f"{days} day{'s' if days != 1 else ''} 🥉")
                highest_unit_found = True
            else:
                time_parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            if not highest_unit_found:
                time_parts.append(f"{hours} hour{'s' if hours != 1 else ''} ⭐")
                highest_unit_found = True
            else:
                time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            if not highest_unit_found:
                time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''} 💫")
                highest_unit_found = True
            else:
                time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 or len(time_parts) == 0:
            if not highest_unit_found:
                time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''} 🔹")
            else:
                time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        # Get overall rating based on highest time unit
        if years >= 10:
            overall_rating = "👑 LEGENDARY ABSTINENCE DEITY"
        elif years >= 1:
            overall_rating = "🏆 EPIC ABSTINENCE MASTER"
        elif months >= 1:
            overall_rating = "🥇 MASTER ABSTAINER"
        elif weeks >= 1:
            overall_rating = "🥈 EXPERT RESTRAINT"
        elif days >= 1:
            overall_rating = "🥉 SKILLED PATIENCE"
        elif hours >= 1:
            overall_rating = "⭐ DECENT CONTROL"
        elif minutes >= 1:
            overall_rating = "💫 BASIC WILLPOWER"
        else:
            overall_rating = "🔹 ROOKIE STATUS"
        
        time_breakdown = " + ".join(time_parts)
        return time_breakdown, overall_rating
        
    def get_timezone_from_location(self, location_parts):
        """Try to determine timezone from location parts"""
        location = " ".join(location_parts).lower()
        
        # Common timezone mappings
        timezone_map = {
            # US Cities
            'new york': 'America/New_York', 'nyc': 'America/New_York',
            'los angeles': 'America/Los_Angeles', 'la': 'America/Los_Angeles',
            'chicago': 'America/Chicago', 'houston': 'America/Chicago',
            'phoenix': 'America/Phoenix', 'philadelphia': 'America/New_York',
            'san antonio': 'America/Chicago', 'san diego': 'America/Los_Angeles',
            'dallas': 'America/Chicago', 'san jose': 'America/Los_Angeles',
            'austin': 'America/Chicago', 'jacksonville': 'America/New_York',
            'san francisco': 'America/Los_Angeles', 'columbus': 'America/New_York',
            'charlotte': 'America/New_York', 'fort worth': 'America/Chicago',
            'indianapolis': 'America/Indiana/Indianapolis', 'seattle': 'America/Los_Angeles',
            'denver': 'America/Denver', 'washington': 'America/New_York',
            'boston': 'America/New_York', 'el paso': 'America/Denver',
            'detroit': 'America/Detroit', 'nashville': 'America/Chicago',
            'portland': 'America/Los_Angeles', 'memphis': 'America/Chicago',
            'oklahoma city': 'America/Chicago', 'las vegas': 'America/Los_Angeles',
            'louisville': 'America/New_York', 'baltimore': 'America/New_York',
            'milwaukee': 'America/Chicago', 'albuquerque': 'America/Denver',
            'tucson': 'America/Phoenix', 'fresno': 'America/Los_Angeles',
            'sacramento': 'America/Los_Angeles', 'mesa': 'America/Phoenix',
            'kansas city': 'America/Chicago', 'atlanta': 'America/New_York',
            'miami': 'America/New_York', 'colorado springs': 'America/Denver',
            'raleigh': 'America/New_York', 'omaha': 'America/Chicago',
            'long beach': 'America/Los_Angeles', 'virginia beach': 'America/New_York',
            'oakland': 'America/Los_Angeles', 'minneapolis': 'America/Chicago',
            'tulsa': 'America/Chicago', 'arlington': 'America/Chicago',
            'tampa': 'America/New_York', 'new orleans': 'America/Chicago',
            'wichita': 'America/Chicago', 'cleveland': 'America/New_York',
            'bakersfield': 'America/Los_Angeles', 'aurora': 'America/Denver',
            'anaheim': 'America/Los_Angeles', 'honolulu': 'Pacific/Honolulu',
            'santa ana': 'America/Los_Angeles', 'corpus christi': 'America/Chicago',
            'riverside': 'America/Los_Angeles', 'lexington': 'America/New_York',
            'stockton': 'America/Los_Angeles', 'st. louis': 'America/Chicago',
            'saint paul': 'America/Chicago', 'cincinnati': 'America/New_York',
            'anchorage': 'America/Anchorage', 'henderson': 'America/Los_Angeles',
            'greensboro': 'America/New_York', 'plano': 'America/Chicago',
            'newark': 'America/New_York', 'lincoln': 'America/Chicago',
            'buffalo': 'America/New_York', 'jersey city': 'America/New_York',
            'chula vista': 'America/Los_Angeles', 'fort wayne': 'America/Indiana/Indianapolis',
            'orlando': 'America/New_York', 'st. petersburg': 'America/New_York',
            'chandler': 'America/Phoenix', 'laredo': 'America/Chicago',
            'norfolk': 'America/New_York', 'durham': 'America/New_York',
            'madison': 'America/Chicago', 'lubbock': 'America/Chicago',
            'irvine': 'America/Los_Angeles', 'winston-salem': 'America/New_York',
            'glendale': 'America/Los_Angeles', 'garland': 'America/Chicago',
            'hialeah': 'America/New_York', 'reno': 'America/Los_Angeles',
            'baton rouge': 'America/Chicago', 'irving': 'America/Chicago',
            'scottsdale': 'America/Phoenix', 'fremont': 'America/Los_Angeles',
            'boise': 'America/Boise', 'richmond': 'America/New_York',
            'san bernardino': 'America/Los_Angeles', 'birmingham': 'America/Chicago',
            'spokane': 'America/Los_Angeles', 'rochester': 'America/New_York',
            'des moines': 'America/Chicago', 'modesto': 'America/Los_Angeles',
            'fayetteville': 'America/New_York', 'tacoma': 'America/Los_Angeles',
            'oxnard': 'America/Los_Angeles', 'fontana': 'America/Los_Angeles',
            'columbus': 'America/New_York', 'montgomery': 'America/Chicago',
            'moreno valley': 'America/Los_Angeles', 'shreveport': 'America/Chicago',
            'aurora': 'America/Chicago', 'yonkers': 'America/New_York',
            'akron': 'America/New_York', 'huntington beach': 'America/Los_Angeles',
            'little rock': 'America/Chicago', 'augusta': 'America/New_York',
            'amarillo': 'America/Chicago', 'glendale': 'America/Phoenix',
            'mobile': 'America/Chicago', 'grand rapids': 'America/New_York',
            'salt lake city': 'America/Denver', 'tallahassee': 'America/New_York',
            'huntsville': 'America/Chicago', 'grand prairie': 'America/Chicago',
            'knoxville': 'America/New_York', 'worcester': 'America/New_York',
            'newport news': 'America/New_York', 'brownsville': 'America/Chicago',
            'santa clarita': 'America/Los_Angeles', 'providence': 'America/New_York',
            'fort lauderdale': 'America/New_York', 'chattanooga': 'America/New_York',
            'tempe': 'America/Phoenix', 'oceanside': 'America/Los_Angeles',
            'garden grove': 'America/Los_Angeles', 'rancho cucamonga': 'America/Los_Angeles',
            'cape coral': 'America/New_York', 'santa rosa': 'America/Los_Angeles',
            'vancouver': 'America/Los_Angeles', 'sioux falls': 'America/Chicago',
            'ontario': 'America/Los_Angeles', 'mckinney': 'America/Chicago',
            'elk grove': 'America/Los_Angeles', 'pembroke pines': 'America/New_York',
            'salem': 'America/Los_Angeles', 'corona': 'America/Los_Angeles',
            
            # US States
            'california': 'America/Los_Angeles', 'ca': 'America/Los_Angeles',
            'new york': 'America/New_York', 'ny': 'America/New_York',
            'texas': 'America/Chicago', 'tx': 'America/Chicago',
            'florida': 'America/New_York', 'fl': 'America/New_York',
            'pennsylvania': 'America/New_York', 'pa': 'America/New_York',
            'illinois': 'America/Chicago', 'il': 'America/Chicago',
            'ohio': 'America/New_York', 'oh': 'America/New_York',
            'georgia': 'America/New_York', 'ga': 'America/New_York',
            'north carolina': 'America/New_York', 'nc': 'America/New_York',
            'michigan': 'America/Detroit', 'mi': 'America/Detroit',
            'new jersey': 'America/New_York', 'nj': 'America/New_York',
            'virginia': 'America/New_York', 'va': 'America/New_York',
            'washington': 'America/Los_Angeles', 'wa': 'America/Los_Angeles',
            'arizona': 'America/Phoenix', 'az': 'America/Phoenix',
            'massachusetts': 'America/New_York', 'ma': 'America/New_York',
            'tennessee': 'America/Chicago', 'tn': 'America/Chicago',
            'indiana': 'America/Indiana/Indianapolis', 'in': 'America/Indiana/Indianapolis',
            'missouri': 'America/Chicago', 'mo': 'America/Chicago',
            'maryland': 'America/New_York', 'md': 'America/New_York',
            'wisconsin': 'America/Chicago', 'wi': 'America/Chicago',
            'colorado': 'America/Denver', 'co': 'America/Denver',
            'minnesota': 'America/Chicago', 'mn': 'America/Chicago',
            'south carolina': 'America/New_York', 'sc': 'America/New_York',
            'alabama': 'America/Chicago', 'al': 'America/Chicago',
            'louisiana': 'America/Chicago', 'la': 'America/Chicago',
            'kentucky': 'America/New_York', 'ky': 'America/New_York',
            'oregon': 'America/Los_Angeles', 'or': 'America/Los_Angeles',
            'oklahoma': 'America/Chicago', 'ok': 'America/Chicago',
            'connecticut': 'America/New_York', 'ct': 'America/New_York',
            'utah': 'America/Denver', 'ut': 'America/Denver',
            'iowa': 'America/Chicago', 'ia': 'America/Chicago',
            'nevada': 'America/Los_Angeles', 'nv': 'America/Los_Angeles',
            'arkansas': 'America/Chicago', 'ar': 'America/Chicago',
            'mississippi': 'America/Chicago', 'ms': 'America/Chicago',
            'kansas': 'America/Chicago', 'ks': 'America/Chicago',
            'new mexico': 'America/Denver', 'nm': 'America/Denver',
            'nebraska': 'America/Chicago', 'ne': 'America/Chicago',
            'west virginia': 'America/New_York', 'wv': 'America/New_York',
            'idaho': 'America/Boise', 'id': 'America/Boise',
            'hawaii': 'Pacific/Honolulu', 'hi': 'Pacific/Honolulu',
            'new hampshire': 'America/New_York', 'nh': 'America/New_York',
            'maine': 'America/New_York', 'me': 'America/New_York',
            'montana': 'America/Denver', 'mt': 'America/Denver',
            'rhode island': 'America/New_York', 'ri': 'America/New_York',
            'delaware': 'America/New_York', 'de': 'America/New_York',
            'south dakota': 'America/Chicago', 'sd': 'America/Chicago',
            'north dakota': 'America/Chicago', 'nd': 'America/Chicago',
            'alaska': 'America/Anchorage', 'ak': 'America/Anchorage',
            'vermont': 'America/New_York', 'vt': 'America/New_York',
            'wyoming': 'America/Denver', 'wy': 'America/Denver',
            
            # Countries
            'usa': 'America/New_York', 'united states': 'America/New_York',
            'canada': 'America/Toronto', 'toronto': 'America/Toronto',
            'vancouver': 'America/Vancouver', 'montreal': 'America/Montreal',
            'calgary': 'America/Calgary', 'edmonton': 'America/Edmonton',
            'ottawa': 'America/Toronto', 'winnipeg': 'America/Winnipeg',
            'quebec': 'America/Montreal', 'hamilton': 'America/Toronto',
            'kitchener': 'America/Toronto', 'london': 'America/Toronto',
            'halifax': 'America/Halifax', 'victoria': 'America/Vancouver',
            'saskatoon': 'America/Regina', 'regina': 'America/Regina',
            
            'uk': 'Europe/London', 'united kingdom': 'Europe/London',
            'london': 'Europe/London', 'manchester': 'Europe/London',
            'birmingham': 'Europe/London', 'glasgow': 'Europe/London',
            'liverpool': 'Europe/London', 'leeds': 'Europe/London',
            'sheffield': 'Europe/London', 'edinburgh': 'Europe/London',
            'bristol': 'Europe/London', 'cardiff': 'Europe/London',
            'belfast': 'Europe/London', 'newcastle': 'Europe/London',
            
            'germany': 'Europe/Berlin', 'berlin': 'Europe/Berlin',
            'munich': 'Europe/Berlin', 'hamburg': 'Europe/Berlin',
            'cologne': 'Europe/Berlin', 'frankfurt': 'Europe/Berlin',
            'stuttgart': 'Europe/Berlin', 'düsseldorf': 'Europe/Berlin',
            'dortmund': 'Europe/Berlin', 'essen': 'Europe/Berlin',
            
            'france': 'Europe/Paris', 'paris': 'Europe/Paris',
            'marseille': 'Europe/Paris', 'lyon': 'Europe/Paris',
            'toulouse': 'Europe/Paris', 'nice': 'Europe/Paris',
            'nantes': 'Europe/Paris', 'montpellier': 'Europe/Paris',
            'strasbourg': 'Europe/Paris', 'bordeaux': 'Europe/Paris',
            
            'australia': 'Australia/Sydney', 'sydney': 'Australia/Sydney',
            'melbourne': 'Australia/Melbourne', 'brisbane': 'Australia/Brisbane',
            'perth': 'Australia/Perth', 'adelaide': 'Australia/Adelaide',
            'canberra': 'Australia/Sydney', 'darwin': 'Australia/Darwin',
            'hobart': 'Australia/Hobart',
            
            'japan': 'Asia/Tokyo', 'tokyo': 'Asia/Tokyo',
            'osaka': 'Asia/Tokyo', 'kyoto': 'Asia/Tokyo',
            'nagoya': 'Asia/Tokyo', 'sapporo': 'Asia/Tokyo',
            'fukuoka': 'Asia/Tokyo', 'kobe': 'Asia/Tokyo',
            
            'china': 'Asia/Shanghai', 'beijing': 'Asia/Shanghai',
            'shanghai': 'Asia/Shanghai', 'guangzhou': 'Asia/Shanghai',
            'shenzhen': 'Asia/Shanghai', 'tianjin': 'Asia/Shanghai',
            'wuhan': 'Asia/Shanghai', 'xi\'an': 'Asia/Shanghai',
            
            'india': 'Asia/Kolkata', 'mumbai': 'Asia/Kolkata',
            'delhi': 'Asia/Kolkata', 'bangalore': 'Asia/Kolkata',
            'hyderabad': 'Asia/Kolkata', 'chennai': 'Asia/Kolkata',
            'kolkata': 'Asia/Kolkata', 'pune': 'Asia/Kolkata',
            
            'brazil': 'America/Sao_Paulo', 'sao paulo': 'America/Sao_Paulo',
            'rio de janeiro': 'America/Sao_Paulo', 'brasilia': 'America/Sao_Paulo',
            'salvador': 'America/Sao_Paulo', 'fortaleza': 'America/Sao_Paulo',
            
            'mexico': 'America/Mexico_City', 'mexico city': 'America/Mexico_City',
            'guadalajara': 'America/Mexico_City', 'monterrey': 'America/Mexico_City',
            'puebla': 'America/Mexico_City', 'tijuana': 'America/Tijuana',
            'juarez': 'America/Denver', 'leon': 'America/Mexico_City',
            
            'netherlands': 'Europe/Amsterdam', 'amsterdam': 'Europe/Amsterdam',
            'rotterdam': 'Europe/Amsterdam', 'the hague': 'Europe/Amsterdam',
            'utrecht': 'Europe/Amsterdam',
            
            'spain': 'Europe/Madrid', 'madrid': 'Europe/Madrid',
            'barcelona': 'Europe/Madrid', 'valencia': 'Europe/Madrid',
            'seville': 'Europe/Madrid', 'bilbao': 'Europe/Madrid',
            
            'italy': 'Europe/Rome', 'rome': 'Europe/Rome',
            'milan': 'Europe/Rome', 'naples': 'Europe/Rome',
            'turin': 'Europe/Rome', 'florence': 'Europe/Rome',
            
            'russia': 'Europe/Moscow', 'moscow': 'Europe/Moscow',
            'saint petersburg': 'Europe/Moscow', 'novosibirsk': 'Asia/Novosibirsk',
            'yekaterinburg': 'Asia/Yekaterinburg', 'nizhny novgorod': 'Europe/Moscow',
        }
        
        # Check for exact matches first
        if location in timezone_map:
            return timezone_map[location]
        
        # Check for partial matches
        for key, tz in timezone_map.items():
            if key in location or location in key:
                return tz
        
        return None
        
    def get_user_datetime(self, nick):
        """Get datetime in user's timezone, or server timezone if not set"""
        if nick in self.user_timezones:
            try:
                user_tz = ZoneInfo(self.user_timezones[nick])
                return datetime.now(user_tz)
            except:
                pass
        return datetime.now()
        
    def calculate_precision_score(self, nick, user_datetime, current_time):
        """Calculate precision timing score for 4:20 attempts"""
        if nick not in self.precision_timing:
            self.precision_timing[nick] = {
                'last_420_time': None,
                'perfect_cycles': 0,
                'total_420s': 0,
                'best_precision': float('inf'),
                'cycle_streak': 0
            }
        
        timing_data = self.precision_timing[nick]
        
        # Calculate how many seconds off from perfect 4:20
        current_minute = user_datetime.minute
        current_second = user_datetime.second
        
        # Calculate seconds from 4:20:00
        seconds_from_420 = abs((current_minute - 20) * 60 + current_second)
        if seconds_from_420 > 30 * 60:  # If more than 30 minutes off, they're probably aiming for the other 4:20
            seconds_from_420 = 60 * 60 - seconds_from_420
        
        # Update best precision if this is better
        if seconds_from_420 < timing_data['best_precision']:
            timing_data['best_precision'] = seconds_from_420
        
        # Check if this maintains a 12-hour cycle
        is_perfect_cycle = False
        if timing_data['last_420_time']:
            time_since_last = current_time - timing_data['last_420_time']
            hours_since_last = time_since_last / 3600
            
            # Check if it's close to a 12-hour multiple (within 1 hour tolerance)
            cycle_multiples = [12, 24, 36, 48]  # 12, 24, 36, 48 hour cycles
            for cycle_hours in cycle_multiples:
                if abs(hours_since_last - cycle_hours) <= 1:  # 1 hour tolerance
                    is_perfect_cycle = True
                    timing_data['perfect_cycles'] += 1
                    timing_data['cycle_streak'] += 1
                    break
            
            if not is_perfect_cycle:
                timing_data['cycle_streak'] = 0  # Reset streak if cycle is broken
        else:
            # First 4:20, start the cycle
            timing_data['cycle_streak'] = 1
        
        timing_data['total_420s'] += 1
        timing_data['last_420_time'] = current_time
        
        # Calculate precision rank
        precision_rank = self.get_precision_rank(seconds_from_420, timing_data['perfect_cycles'], timing_data['cycle_streak'])
        
        return seconds_from_420, is_perfect_cycle, precision_rank, timing_data
    
    def get_precision_rank(self, seconds_off, perfect_cycles, cycle_streak):
        """Get precision rank based on timing accuracy and cycle maintenance"""
        # Base rank on precision (lower seconds = better rank)
        if seconds_off == 0:
            base_rank = "🏆 PERFECT CHRONOS"
        elif seconds_off <= 5:
            base_rank = "🥇 MASTER TIMER"
        elif seconds_off <= 15:
            base_rank = "🥈 EXPERT PRECISION"
        elif seconds_off <= 30:
            base_rank = "🥉 SKILLED TIMING"
        elif seconds_off <= 60:
            base_rank = "⭐ DECENT ACCURACY"
        elif seconds_off <= 120:
            base_rank = "💫 BASIC ATTEMPT"
        else:
            base_rank = "🔹 ROOKIE TIMING"
        
        # Enhance rank based on perfect cycles and streaks
        if cycle_streak >= 7:
            enhanced_rank = f"👑 LEGENDARY CYCLE MASTER - {base_rank}"
        elif cycle_streak >= 5:
            enhanced_rank = f"🔥 FIRE STREAK CHAMPION - {base_rank}"
        elif cycle_streak >= 3:
            enhanced_rank = f"⚡ LIGHTNING STREAK - {base_rank}"
        elif perfect_cycles >= 10:
            enhanced_rank = f"🌌 COSMIC SYNCHRONIZER - {base_rank}"
        elif perfect_cycles >= 5:
            enhanced_rank = f"🌀 CYCLONE MASTER - {base_rank}"
        elif perfect_cycles >= 1:
            enhanced_rank = f"🔄 CYCLE KEEPER - {base_rank}"
        else:
            enhanced_rank = base_rank
        
        return enhanced_rank
        
    def get_stoner_rank(self, seconds_abstinent):
        """Get humorous stoner ranking based on abstinence time"""
        days = seconds_abstinent // 86400
        hours = (seconds_abstinent % 86400) // 3600
        minutes = (seconds_abstinent % 3600) // 60
        
        # Humorous stoner abstinence rankings (longest = highest rank)
        if days >= 365:  # 1+ years
            return "👑 LEGENDARY SOBER SAGE"
        elif days >= 180:  # 6+ months
            return "🧿 ENLIGHTENED MONK OF SOBRIETY"
        elif days >= 90:   # 3+ months
            return "🧘 ZEN MASTER OF RESTRAINT"
        elif days >= 30:   # 1+ months
            return "🌱 CANNABIS CLEANSE CHAMPION"
        elif days >= 14:   # 2+ weeks
            return "🏆 T-BREAK TITAN"
        elif days >= 7:    # 1+ weeks
            return "🥇 WILLPOWER WARRIOR"
        elif days >= 3:    # 3+ days
            return "🥈 ABSTINENCE APPRENTICE"
        elif days >= 1:    # 1+ days
            return "🥉 SOBER SOLDIER"
        elif hours >= 12:  # 12+ hours
            return "⭐ HALF-DAY HERO"
        elif hours >= 6:   # 6+ hours
            return "🌅 SUNRISE SURVIVOR"
        elif hours >= 3:   # 3+ hours
            return "🕰️ THREE-HOUR TROUPER"
        elif hours >= 1:   # 1+ hours
            return "⏰ HOURLY HOLDOUT"
        elif minutes >= 30: # 30+ minutes
            return "💫 HALF-HOUR HUSTLER"
        elif minutes >= 15: # 15+ minutes
            return "🔕 QUARTER-HOUR QUITTER"
        elif minutes >= 5:  # 5+ minutes
            return "🚀 FIVE-MINUTE FIGHTER"
        elif minutes >= 1:  # 1+ minutes
            return "🔹 MINUTE-MAN ROOKIE"
        else:               # Under 1 minute
            return "🍃 FRESH TOKER"
        
    def connect(self):
        """Connect to the IRC server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server, self.port))
            self.connected = True
            
            # Send IRC connection commands
            self.send_raw(f"NICK {self.nickname}")
            self.send_raw(f"USER {self.username} 0 * :{self.realname}")
            
            self.logger.info(f"Connected to {self.server}:{self.port}")
            return True
            
        except Exception as e:
            self.logger.error(f"Connection failed: {e}")
            return False
            
    def send_raw(self, message):
        """Send raw IRC message"""
        if self.socket:
            full_message = message + "\r\n"
            self.socket.send(full_message.encode('utf-8'))
            self.logger.debug(f"SENT: {message}")
            
    def send_message(self, channel, message):
        """Send message to a channel"""
        self.send_raw(f"PRIVMSG {channel} :{message}")
        
    def join_channel(self, channel):
        """Join a channel"""
        self.send_raw(f"JOIN {channel}")
        self.logger.info(f"Joined {channel}")
        
    def handle_ping(self, message):
        """Handle PING messages from server"""
        if message.startswith("PING"):
            pong_message = message.replace("PING", "PONG", 1)
            self.send_raw(pong_message)
            
    def parse_message(self, raw_message):
        """Parse IRC message and extract components"""
        parts = raw_message.split(' ', 3)
        if len(parts) < 3:
            return None
            
        prefix = parts[0][1:] if parts[0].startswith(':') else ""
        command = parts[1]
        target = parts[2]
        message = parts[3][1:] if len(parts) > 3 and parts[3].startswith(':') else ""
        
        # Extract nickname from prefix
        nick = prefix.split('!')[0] if '!' in prefix else ""
        
        return {
            'prefix': prefix,
            'nick': nick,
            'command': command,
            'target': target,
            'message': message,
            'raw': raw_message
        }
        
    def handle_command(self, parsed_msg):
        """Handle bot commands"""
        if not parsed_msg['message'].startswith(self.command_prefix):
            return
            
        command_parts = parsed_msg['message'][1:].split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        nick = parsed_msg['nick']
        channel = parsed_msg['target']
        
        if command == "bud-zone":
            if not args:
                # Show current timezone
                if nick in self.user_timezones:
                    current_tz = self.user_timezones[nick]
                    user_dt = self.get_user_datetime(nick)
                    self.send_message(channel, f"{nick}: Your bud-zone is set to {current_tz} (currently {user_dt.strftime('%I:%M %p %Z')} 🌍🌿)")
                else:
                    self.send_message(channel, f"{nick}: You haven't set a bud-zone yet! Use: !bud-zone <city state country> 🌍🌿")
            else:
                # Set timezone based on location
                location_str = " ".join(args)
                timezone = self.get_timezone_from_location(args)
                
                if timezone:
                    self.user_timezones[nick] = timezone
                    self.save_toke_data()
                    user_dt = self.get_user_datetime(nick)
                    self.send_message(channel, f"{nick}: Bud-zone set to {location_str} ({timezone}) - {user_dt.strftime('%I:%M %p %Z')} 🌍🌿")
                else:
                    self.send_message(channel, f"{nick}: Sorry, couldn't find timezone for '{location_str}'. Try: city, state, country (e.g., 'Los Angeles CA', 'London UK', 'Tokyo Japan') 🌍🌿")
            
        elif command == "strain":
            # Cannabis strain information lookup
            if not args:
                self.send_message(channel, f"{nick}: Use !strain <strain_name> to get info about a cannabis strain! Example: !strain Blue Dream 🌿")
                return
            
            strain_name = " ".join(args).lower()
            
            # Cannabis strain database - Comprehensive collection of 150+ strains
            strain_db = {
                # Classic & Legendary Strains
                "blue dream": "Hybrid 🌿 Blue Dream is a sativa-dominant hybrid with balanced full-body relaxation and gentle cerebral invigoration. Perfect for daytime use with creative energy. THC: 17-24% | Effects: Happy, Relaxed, Euphoric, Creative | Flavors: Sweet berry, blueberry",
                "og kush": "Hybrid 🌿 OG Kush is a legendary strain with distinct earthy, pine and woody flavors. Delivers heavy-hitting euphoria and relaxation. THC: 20-26% | Effects: Euphoric, Happy, Relaxed, Uplifted | Flavors: Earthy, pine, woody",
                "sour diesel": "Sativa 🌿 Sour Diesel (Sour D) is a fast-acting energizing strain with dreamy cerebral effects. Great for stress relief. THC: 20-25% | Effects: Energetic, Creative, Euphoric, Uplifted | Flavors: Diesel, pungent, citrus",
                "girl scout cookies": "Hybrid 🌿 GSC delivers euphoria and full-body relaxation. Known for sweet and earthy aromas. THC: 25-28% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Sweet, earthy, mint",
                "gsc": "Hybrid 🌿 GSC delivers euphoria and full-body relaxation. Known for sweet and earthy aromas. THC: 25-28% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Sweet, earthy, mint",
                "granddaddy purple": "Indica 🌿 Granddaddy Purple (GDP) combines Mendo Purps, Skunk, and Afghan genetics for potent indica effects. Deep relaxation. THC: 17-24% | Effects: Relaxed, Sleepy, Euphoric, Happy | Flavors: Grape, berry, sweet",
                "gdp": "Indica 🌿 Granddaddy Purple (GDP) combines Mendo Purps, Skunk, and Afghan genetics for potent indica effects. Deep relaxation. THC: 17-24% | Effects: Relaxed, Sleepy, Euphoric, Happy | Flavors: Grape, berry, sweet",
                "white widow": "Hybrid 🌿 White Widow is a balanced hybrid with powerful bursts of euphoria and energy. Legendary since the 90s. THC: 18-25% | Effects: Energetic, Euphoric, Creative, Uplifted | Flavors: Earthy, woody, pine",
                "northern lights": "Indica 🌿 Northern Lights is a pure indica with fast-acting psychoactive effects. One of the most famous strains. THC: 16-21% | Effects: Relaxed, Sleepy, Euphoric, Happy | Flavors: Sweet, spicy, earthy",
                "jack herer": "Sativa 🌿 Jack Herer is a blissful, clear-headed and creative sativa strain. Named after the cannabis activist. THC: 18-24% | Effects: Energetic, Creative, Euphoric, Uplifted | Flavors: Earthy, pine, woody",
                "green crack": "Sativa 🌿 Green Crack provides invigorating mental buzz and sharp energy. Great for daytime use. THC: 15-25% | Effects: Energetic, Focused, Creative, Happy | Flavors: Sweet, citrus, fruity",
                "ak-47": "Hybrid 🌿 AK-47 is a sativa-dominant hybrid that delivers steady cerebral buzz with mellow relaxation. Long-lasting. THC: 13-20% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Earthy, sweet, pungent",
                "durban poison": "Sativa 🌿 Durban Poison is a pure sativa with energetic, uplifting effects. Perfect for staying productive. THC: 15-25% | Effects: Energetic, Happy, Focused, Creative | Flavors: Sweet, earthy, pine",
                "pineapple express": "Hybrid 🌿 Pineapple Express delivers long-lasting energetic buzz. Made famous by the movie. THC: 17-24% | Effects: Energetic, Happy, Euphoric, Creative | Flavors: Tropical, pineapple, citrus",
                "acapulco gold": "Sativa 🌿 Acapulco Gold is a legendary strain with euphoric, energizing effects. Rare and potent. THC: 15-24% | Effects: Energetic, Euphoric, Happy, Creative | Flavors: Earthy, sweet, toffee",
                "maui wowie": "Sativa 🌿 Maui Wowie brings tropical euphoria and creative energy. Classic Hawaiian strain. THC: 13-19% | Effects: Energetic, Creative, Happy, Euphoric | Flavors: Tropical, pineapple, sweet",
                "purple haze": "Sativa 🌿 Purple Haze delivers dreamy cerebral high with creativity. Made famous by Jimi Hendrix. THC: 15-20% | Effects: Energetic, Creative, Euphoric, Happy | Flavors: Sweet, berry, earthy",
                
                # Modern Hybrids & Crosses
                "gorilla glue": "Hybrid 🌿 Gorilla Glue #4 delivers heavy-handed euphoria and relaxation. Very potent and sticky. THC: 25-30% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Earthy, pungent, pine",
                "gg4": "Hybrid 🌿 Gorilla Glue #4 delivers heavy-handed euphoria and relaxation. Very potent and sticky. THC: 25-30% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Earthy, pungent, pine",
                "gelato": "Hybrid 🌿 Gelato is a sweet, dessert-like strain with euphoric and relaxing effects. Very flavorful. THC: 20-26% | Effects: Euphoric, Relaxed, Happy, Creative | Flavors: Sweet, berry, lavender",
                "wedding cake": "Indica 🌿 Wedding Cake provides calming and euphoric effects. Rich, tangy flavor profile. THC: 21-27% | Effects: Relaxed, Euphoric, Happy, Calm | Flavors: Sweet, earthy, vanilla",
                "runtz": "Hybrid 🌿 Runtz provides euphoric high with fruity, candy-like flavors. Evenly balanced. THC: 19-29% | Effects: Relaxed, Euphoric, Happy, Calm | Flavors: Fruity, sweet, tropical",
                "zkittlez": "Indica 🌿 Zkittlez offers fruity, tropical flavors with calming, happy effects. Award-winning strain. THC: 15-23% | Effects: Relaxed, Happy, Euphoric, Calm | Flavors: Fruity, tropical, sweet",
                "mac": "Hybrid 🌿 Miracle Alien Cookies (MAC) delivers uplifting and balancing effects. Unique flavor. THC: 20-25% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Citrus, floral, herbal",
                "do-si-dos": "Indica 🌿 Do-Si-Dos delivers heavy stoning body high and cerebral euphoria. Very potent. THC: 19-30% | Effects: Relaxed, Euphoric, Sleepy, Happy | Flavors: Sweet, earthy, floral",
                "wedding crasher": "Hybrid 🌿 Wedding Crasher blends Wedding Cake and Purple Punch for sweet relaxation. THC: 18-25% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Grape, vanilla, sweet",
                "ice cream cake": "Indica 🌿 Ice Cream Cake delivers sedating effects with creamy vanilla flavors. Very relaxing. THC: 20-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Vanilla, cream, sweet",
                "biscotti": "Indica 🌿 Biscotti provides powerful relaxation with sweet, spicy cookie flavors. THC: 21-25% | Effects: Relaxed, Euphoric, Happy, Calm | Flavors: Sweet, spicy, nutty",
                "london pound cake": "Indica 🌿 London Pound Cake delivers relaxing body high with sweet berry flavors. THC: 20-26% | Effects: Relaxed, Happy, Sleepy, Euphoric | Flavors: Berry, sweet, lemon",
                "jealousy": "Hybrid 🌿 Jealousy combines Gelato 41 with Sherbet for balanced euphoric effects. THC: 20-28% | Effects: Euphoric, Relaxed, Happy, Creative | Flavors: Sweet, earthy, citrus",
                
                # Kush Family
                "bubba kush": "Indica 🌿 Bubba Kush delivers tranquilizing relaxation with sweet hashish flavors. Heavy indica. THC: 14-22% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Earthy, sweet, hash",
                "skywalker og": "Indica 🌿 Skywalker OG blends potent OG Kush with Skywalker for heavy relaxation. Strong indica. THC: 20-26% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Spicy, herbal, earthy",
                "pink kush": "Indica 🌿 Pink Kush delivers powerful body high with sweet vanilla and floral flavors. THC: 18-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Sweet, vanilla, floral",
                "critical kush": "Indica 🌿 Critical Kush combines OG Kush and Critical Mass for sedating body effects. THC: 20-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Earthy, spicy, pine",
                "banana kush": "Hybrid 🌿 Banana Kush blends Ghost OG and Skunk Haze for tropical relaxation. THC: 18-25% | Effects: Happy, Euphoric, Relaxed, Uplifted | Flavors: Banana, tropical, sweet",
                "master kush": "Indica 🌿 Master Kush is a Dutch classic with sharp earthy, citrus flavors and full-body relaxation. THC: 20-24% | Effects: Relaxed, Happy, Sleepy, Euphoric | Flavors: Earthy, citrus, pungent",
                "platinum kush": "Indica 🌿 Platinum Kush delivers strong sedation with earthy, hashy flavors. Very potent. THC: 18-24% | Effects: Relaxed, Sleepy, Happy, Calm | Flavors: Earthy, hash, spicy",
                "hindu kush": "Indica 🌿 Hindu Kush is a pure landrace indica from the Hindu Kush mountains. Deep relaxation. THC: 15-20% | Effects: Relaxed, Sleepy, Happy, Calm | Flavors: Earthy, sweet, sandalwood",
                "purple kush": "Indica 🌿 Purple Kush is a pure indica with long-lasting physical relaxation and blissful effects. THC: 17-27% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Grape, earthy, sweet",
                "kosher kush": "Indica 🌿 Kosher Kush is a potent indica with rich earthy and fruity flavors. Award winner. THC: 20-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Earthy, fruity, pine",
                
                # Cookies & Dessert Strains
                "cookies": "Hybrid 🌿 Cookies family strains deliver euphoria and full-body relaxation. Sweet earthy flavors. THC: 20-28% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Sweet, earthy, nutty",
                "thin mint cookies": "Hybrid 🌿 Thin Mint GSC delivers minty, sweet flavors with powerful euphoric effects. THC: 20-24% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Mint, sweet, earthy",
                "animal cookies": "Hybrid 🌿 Animal Cookies crosses GSC with Fire OG for powerful sedating effects. THC: 20-27% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Sweet, sour, earthy",
                "cereal milk": "Hybrid 🌿 Cereal Milk tastes like sweet milk and ice cream with balanced hybrid effects. THC: 18-23% | Effects: Happy, Relaxed, Euphoric, Calm | Flavors: Cream, sweet, berry",
                "birthday cake": "Hybrid 🌿 Birthday Cake delivers euphoric relaxation with sweet vanilla and creamy flavors. THC: 21-26% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Vanilla, sweet, cream",
                
                # Purple & Berry Strains
                "purple punch": "Indica 🌿 Purple Punch delivers sedating body high with sweet grape and blueberry flavors. THC: 18-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Grape, blueberry, sweet",
                "cherry pie": "Hybrid 🌿 Cherry Pie combines sweet cherry and earthy flavors with relaxing, euphoric effects. THC: 16-24% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Cherry, sweet, earthy",
                "forbidden fruit": "Indica 🌿 Forbidden Fruit brings deep relaxation with cherry, lemon and tropical flavors. THC: 18-26% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Cherry, lemon, tropical",
                "blueberry": "Indica 🌿 Blueberry is a legendary strain with sweet berry flavors and relaxing body effects. THC: 16-24% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Blueberry, sweet, berry",
                "blackberry kush": "Indica 🌿 Blackberry Kush delivers powerful body effects with sweet berry and diesel flavors. THC: 16-20% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Berry, diesel, earthy",
                "grape ape": "Indica 🌿 Grape Ape provides deep relaxation with distinct grape and berry flavors. THC: 18-25% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Grape, berry, sweet",
                "strawberry cough": "Sativa 🌿 Strawberry Cough delivers energetic cerebral high with sweet strawberry flavor. THC: 15-20% | Effects: Energetic, Happy, Euphoric, Uplifted | Flavors: Strawberry, sweet, berry",
                
                # Citrus & Haze Strains
                "tangie": "Sativa 🌿 Tangie provides uplifting euphoria with refreshing citrus tangerine flavors. THC: 19-22% | Effects: Energetic, Happy, Creative, Euphoric | Flavors: Citrus, tangerine, sweet",
                "super lemon haze": "Sativa 🌿 Super Lemon Haze provides energetic, talkative euphoria with zesty citrus flavor. THC: 16-22% | Effects: Energetic, Happy, Euphoric, Uplifted | Flavors: Lemon, citrus, sweet",
                "lemon haze": "Sativa 🌿 Lemon Haze delivers creative energy with strong lemon and citrus flavors. THC: 15-21% | Effects: Energetic, Happy, Euphoric, Creative | Flavors: Lemon, citrus, sweet",
                "amnesia haze": "Sativa 🌿 Amnesia Haze is a potent sativa with uplifting cerebral effects and citrus flavors. THC: 20-25% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Citrus, earthy, spicy",
                "orange cookies": "Hybrid 🌿 Orange Cookies blends Orange Juice with GSC for citrus-sweet relaxation. THC: 20-25% | Effects: Happy, Relaxed, Euphoric, Creative | Flavors: Orange, sweet, citrus",
                "mimosa": "Sativa 🌿 Mimosa delivers uplifting effects with sweet citrus and tropical fruit flavors. THC: 19-27% | Effects: Energetic, Happy, Euphoric, Focused | Flavors: Citrus, tropical, sweet",
                "clementine": "Sativa 🌿 Clementine provides energetic focus with sweet orange and citrus flavors. THC: 17-27% | Effects: Energetic, Focused, Happy, Creative | Flavors: Citrus, orange, sweet",
                
                # Diesel & Chem Strains
                "chemdog": "Hybrid 🌿 Chemdog delivers powerful cerebral effects with diesel, chemical aromas. Legendary genetics. THC: 20-25% | Effects: Euphoric, Relaxed, Creative, Happy | Flavors: Diesel, pungent, earthy",
                "chemdawg": "Hybrid 🌿 Chemdawg delivers powerful cerebral effects with diesel, chemical aromas. Legendary genetics. THC: 20-25% | Effects: Euphoric, Relaxed, Creative, Happy | Flavors: Diesel, pungent, earthy",
                "stardawg": "Hybrid 🌿 Stardawg blends Chemdawg 4 with Tres Dawg for potent diesel effects. THC: 18-23% | Effects: Energetic, Euphoric, Happy, Uplifted | Flavors: Diesel, pungent, pine",
                "headband": "Hybrid 🌿 Headband crosses OG Kush with Sour Diesel for unique pressure-like effects. THC: 20-27% | Effects: Relaxed, Euphoric, Happy, Creative | Flavors: Lemon, diesel, earthy",
                "nyc diesel": "Sativa 🌿 NYC Diesel provides energizing effects with grapefruit and diesel flavors. THC: 14-21% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Diesel, grapefruit, citrus",
                
                # Exotic & Tropical Strains
                "banana og": "Indica 🌿 Banana OG provides peaceful, laid-back effects with tropical banana flavor. THC: 16-23% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Banana, tropical, sweet",
                "sunset sherbet": "Indica 🌿 Sunset Sherbet provides full-body relaxation with sweet berry and citrus flavors. THC: 15-24% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Sweet, berry, citrus",
                "tropicana cookies": "Hybrid 🌿 Tropicana Cookies delivers uplifting effects with tropical citrus and cookie flavors. THC: 22-28% | Effects: Energetic, Happy, Euphoric, Creative | Flavors: Citrus, tropical, sweet",
                "mango kush": "Hybrid 🌿 Mango Kush blends mango and banana flavors with euphoric, relaxing effects. THC: 11-20% | Effects: Happy, Euphoric, Relaxed, Uplifted | Flavors: Mango, banana, tropical",
                "pineapple kush": "Hybrid 🌿 Pineapple Kush delivers tropical euphoria with sweet pineapple flavors. THC: 16-25% | Effects: Happy, Relaxed, Euphoric, Creative | Flavors: Pineapple, tropical, sweet",
                "papaya": "Indica 🌿 Papaya provides sweet tropical relaxation with fruity papaya flavors. THC: 18-25% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Tropical, fruity, sweet",
                
                # High THC Powerhouses
                "god's gift": "Indica 🌿 God's Gift delivers powerful body effects with grape, citrus and hash flavors. THC: 18-27% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Grape, citrus, hash",
                "death star": "Indica 🌿 Death Star provides powerful euphoria and deep relaxation. Diesel and earthy flavors. THC: 20-27% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Diesel, earthy, pungent",
                "the white": "Hybrid 🌿 The White is covered in trichomes and delivers potent euphoric effects. THC: 20-28% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Earthy, woody, pine",
                "white fire og": "Hybrid 🌿 White Fire OG (WiFi OG) provides potent euphoria with sour, earthy flavors. THC: 22-30% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Sour, earthy, diesel",
                "ghost train haze": "Sativa 🌿 Ghost Train Haze is one of the most potent sativas with citrus and floral notes. THC: 25-28% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Citrus, floral, pine",
                "bruce banner": "Hybrid 🌿 Bruce Banner delivers powerful euphoric effects. Named after the Hulk. Very strong. THC: 24-30% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Diesel, sweet, earthy",
                
                # Balanced & Medicinal
                "harlequin": "Sativa 🌿 Harlequin is a high-CBD strain with clear-headed, relaxed effects. Great for pain. THC: 7-15% CBD: 10-16% | Effects: Relaxed, Focused, Happy, Calm | Flavors: Earthy, mango, sweet",
                "cannatonic": "Hybrid 🌿 Cannatonic is a high-CBD strain with mild euphoria and deep relaxation. THC: 7-15% CBD: 12-17% | Effects: Relaxed, Happy, Calm, Focused | Flavors: Earthy, citrus, pine",
                "acdc": "Sativa 🌿 ACDC is a high-CBD strain with minimal psychoactive effects. Great for daytime. THC: 1-6% CBD: 16-24% | Effects: Relaxed, Focused, Calm, Clear | Flavors: Earthy, woody, pine",
                "charlotte's web": "Sativa 🌿 Charlotte's Web is famous high-CBD strain with minimal THC. Medicinal powerhouse. THC: 0.3% CBD: 17-20% | Effects: Relaxed, Calm, Clear, Focused | Flavors: Earthy, pine, sweet",
                
                # Classic Landrace & Old School
                "thai stick": "Sativa 🌿 Thai Stick is a pure landrace sativa from Thailand with energetic, cerebral effects. THC: 16-24% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Earthy, citrus, tropical",
                "afghan kush": "Indica 🌿 Afghan Kush is a pure indica landrace with heavy sedation and earthy flavors. THC: 17-22% | Effects: Relaxed, Sleepy, Happy, Calm | Flavors: Earthy, sweet, spicy",
                "panama red": "Sativa 🌿 Panama Red is a classic landrace with uplifting, psychedelic effects. THC: 14-18% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Earthy, spicy, sweet",
                "lambs bread": "Sativa 🌿 Lamb's Bread (Lamb's Breath) is a Jamaican landrace with energizing effects. THC: 16-21% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Earthy, cheese, herbal",
                "colombian gold": "Sativa 🌿 Colombian Gold is a classic landrace sativa with uplifting, creative effects. THC: 15-20% | Effects: Energetic, Happy, Creative, Euphoric | Flavors: Skunky, sweet, lemon",
                
                # More Modern Favorites
                "trainwreck": "Hybrid 🌿 Trainwreck hits like a freight train with potent sativa effects. Euphoric and creative. THC: 18-25% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Lemon, pine, earthy",
                "larry og": "Indica 🌿 Larry OG (Lemon Larry) delivers strong relaxation with citrus and pine flavors. THC: 20-27% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Lemon, pine, earthy",
                "sfv og": "Hybrid 🌿 SFV OG (San Fernando Valley OG) provides potent euphoria with earthy pine flavors. THC: 19-25% | Effects: Euphoric, Relaxed, Happy, Creative | Flavors: Pine, lemon, earthy",
                "fire og": "Hybrid 🌿 Fire OG is one of the strongest OG strains with powerful sedating effects. THC: 20-26% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Lemon, earthy, spicy",
                "tahoe og": "Hybrid 🌿 Tahoe OG delivers powerful body effects with earthy lemon flavors. THC: 18-25% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Lemon, earthy, pine",
                "platinum og": "Indica 🌿 Platinum OG is a potent indica with coffee and floral notes. Heavy relaxation. THC: 20-24% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Coffee, floral, pine",
                "louis xiii": "Indica 🌿 Louis XIII (Louie XIII OG) is a rare, potent OG with earthy pine flavors. THC: 22-28% | Effects: Relaxed, Sleepy, Euphoric, Happy | Flavors: Pine, earthy, woody",
                "gushers": "Indica 🌿 Gushers delivers tropical fruity flavors with relaxing, euphoric effects. THC: 17-22% | Effects: Relaxed, Happy, Euphoric, Sleepy | Flavors: Tropical, fruity, sweet",
                "apple fritter": "Hybrid 🌿 Apple Fritter combines apple pastry flavors with balanced euphoric effects. THC: 22-28% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Apple, sweet, earthy",
                "gary payton": "Hybrid 🌿 Gary Payton blends The Y with Snowman for potent diesel-sweet effects. THC: 20-25% | Effects: Euphoric, Relaxed, Happy, Creative | Flavors: Diesel, sweet, spicy",
                "slurricane": "Indica 🌿 Slurricane delivers heavy relaxation with sweet berry and grape flavors. THC: 20-28% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Berry, grape, sweet",
                "candy rain": "Hybrid 🌿 Candy Rain provides sweet fruity flavors with balanced euphoric effects. THC: 18-24% | Effects: Happy, Relaxed, Euphoric, Creative | Flavors: Fruity, sweet, berry",
                "candy land": "Sativa 🌿 Candyland delivers energetic euphoria with sweet earthy flavors. THC: 19-24% | Effects: Energetic, Happy, Euphoric, Creative | Flavors: Sweet, earthy, spicy",
                "cherry garcia": "Hybrid 🌿 Cherry Garcia blends cherry flavors with balanced relaxing effects. THC: 18-22% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Cherry, sweet, earthy",
                "jet fuel": "Hybrid 🌿 Jet Fuel (G6) delivers powerful diesel effects with energizing buzz. THC: 18-22% | Effects: Energetic, Euphoric, Happy, Creative | Flavors: Diesel, pine, skunk",
                "king louis": "Indica 🌿 King Louis XIII provides royal relaxation with pine and earthy flavors. THC: 20-28% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Pine, earthy, woody",
                "la confidential": "Indica 🌿 LA Confidential delivers smooth earthy flavors with deep relaxation. THC: 19-25% | Effects: Relaxed, Sleepy, Happy, Calm | Flavors: Earthy, pine, skunk",
                "mendo breath": "Indica 🌿 Mendo Breath provides sweet vanilla caramel with heavy sedation. THC: 19-24% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Vanilla, caramel, sweet",
                "motorbreath": "Indica 🌿 Motorbreath delivers powerful diesel and earthy relaxation. Very potent. THC: 20-28% | Effects: Relaxed, Euphoric, Happy, Sleepy | Flavors: Diesel, earthy, chemical",
                "ninja fruit": "Hybrid 🌿 Ninja Fruit blends fruity strawberry with balanced euphoric effects. THC: 17-22% | Effects: Happy, Relaxed, Euphoric, Creative | Flavors: Strawberry, fruity, sweet",
                "obama kush": "Indica 🌿 Obama Kush delivers presidential relaxation with earthy pine flavors. THC: 14-21% | Effects: Relaxed, Sleepy, Happy, Calm | Flavors: Earthy, pine, grape",
                "purple trainwreck": "Hybrid 🌿 Purple Trainwreck blends grape flavors with energetic euphoria. THC: 18-23% | Effects: Energetic, Happy, Euphoric, Creative | Flavors: Grape, earthy, sweet",
                "raspberry kush": "Indica 🌿 Raspberry Kush delivers sweet berry with relaxing body effects. THC: 15-24% | Effects: Relaxed, Happy, Sleepy, Euphoric | Flavors: Raspberry, sweet, berry",
                "scout cookies": "Hybrid 🌿 Scout Cookies (Thin Mint GSC phenotype) delivers minty sweet euphoria. THC: 20-24% | Effects: Euphoric, Happy, Relaxed, Creative | Flavors: Mint, sweet, earthy",
                "sherbert": "Indica 🌿 Sherbert (Sunset Sherbet) provides fruity sweet relaxation. THC: 15-24% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Sweet, berry, citrus",
                "space queen": "Sativa 🌿 Space Queen delivers cosmic euphoria with fruity cherry flavors. THC: 16-24% | Effects: Energetic, Euphoric, Creative, Happy | Flavors: Cherry, fruity, pineapple",
                "super silver haze": "Sativa 🌿 Super Silver Haze is a potent sativa with spicy, citrus flavors. Award winner. THC: 18-23% | Effects: Energetic, Euphoric, Happy, Creative | Flavors: Citrus, spicy, earthy",
                "white tahoe cookies": "Hybrid 🌿 White Tahoe Cookies blends sweet earthy with powerful euphoria. THC: 20-27% | Effects: Euphoric, Relaxed, Happy, Creative | Flavors: Sweet, earthy, pine",
                "yeti og": "Indica 🌿 Yeti OG delivers frosty, powerful relaxation with earthy diesel flavors. THC: 18-24% | Effects: Relaxed, Sleepy, Happy, Euphoric | Flavors: Diesel, earthy, pine",
                "z3": "Hybrid 🌿 Z3 (Zkittlez x Wedding Cake) delivers fruity sweet euphoria. THC: 20-25% | Effects: Relaxed, Happy, Euphoric, Creative | Flavors: Fruity, sweet, vanilla",
            }
            
            # Look up strain
            if strain_name in strain_db:
                self.send_message(channel, f"{nick}: {strain_db[strain_name]}")
            else:
                # Partial match search
                matches = [name for name in strain_db.keys() if strain_name in name or name in strain_name]
                if matches:
                    if len(matches) == 1:
                        self.send_message(channel, f"{nick}: Did you mean '{matches[0]}'? {strain_db[matches[0]]}")
                    else:
                        match_list = ", ".join(matches[:5])
                        self.send_message(channel, f"{nick}: Found multiple matches: {match_list}. Be more specific! 🌿")
                else:
                    self.send_message(channel, f"{nick}: Strain '{' '.join(args)}' not found in database. Try: Blue Dream, OG Kush, Sour Diesel, Girl Scout Cookies, etc. 🌿")
        
        elif command == "stoned":
            # Random subliminal weed poetry couplets
            import random
            stoned_couplets = [
                "Smoke rises high, thoughts float free / In this moment, just the herb and me 🌿✨",
                "Green leaves burn, minds expand wide / Riding cosmic waves on this elevated tide 🌊🚀",
                "Time melts away like morning dew / Reality shifts to a different hue 🎨🍃",
                "Ancient plant wisdom fills the air / Consciousness dancing without a care 💫🌬️",
                "Rolling papers hold sacred gold / Stories of peace, forever told 📜✨",
                "Inhale the earth, exhale the stress / Finding zen in the greenness 🧘💚",
                "Purple haze and lazy days / Lost in the aromatic maze 🌸🌀",
                "Trichomes glisten like morning frost / In their beauty, I am lost ❄️🔬",
                "Clouds of thought drift through my brain / Washing worries down the drain ☁️🧠",
                "Sacred smoke curls toward the sky / Watching mundane problems fly 🕊️💨",
                "Green goddess whispers ancient tales / Through valleys of consciousness, on herbal trails 🏔️🌿",
                "Burning bridges to the mundane / Elevating far above the plain 🌉🎈",
                "Sticky fingers, happy mind / Leaving earthly cares behind 🤲💭",
                "Cannabis dreams in technicolor bright / Painting reality with different light 🎨🌈",
                "From seed to smoke, the journey's long / But in this moment, I belong 🌱🔥",
                "Couch-locked but mind is free / Exploring infinity internally ♾️🛋️",
                "Munchies call with siren song / But this high won't last too long 🍕⏰",
                "Red-eyed visions, giggling spells / In this state, all is well 😂👁️",
                "The grinder spins, the ritual begins / Transcending ordinary sins ⚙️✨",
                "Mary Jane, my faithful friend / On you, I can depend 🤝💚",
                "Terpenes dance upon my tongue / Feeling forever young 👅🎵",
                "Slow motion thoughts cascade like rain / Washing clean the daily pain 🌧️💆",
                "In the garden of the mind I roam / This altered state feels like home 🏡🧠",
                "Contemplating universe's mysteries / Through these herbal chemistries 🌌🔬",
                "Every puff a tiny prayer / Sending gratitude through the air 🙏💨",
                "Crystal trichomes catch the light / Everything feels just right 💎✨",
                "Botanical bliss in every breath / Dancing with life, forgetting death 🎭💃",
                "The Buddha smiled when he got high / Understanding earth and sky 😌🌍",
                "Giggling at things that aren't that funny / Life tastes sweeter than honey 🍯😄",
                "Paranoia knocks but I won't answer / Too busy being a cosmic dancer 💃🌟",
                "Sativa thoughts race like the wind / While indica keeps me grinned 🌪️😊",
                "Papers twist, the cone takes shape / Portal to the mind's landscape 🌀🗺️",
                "In the smoke I see the truth / Reclaiming my eternal youth ⏳💫",
                "Gravity feels optional today / As worries simply float away 🎈🌬️",
                "Philosophy becomes so clear / When the herb is near 💡🌿",
                "Creative sparks ignite the brain / Thoughts form patterns like the rain 🧠⚡",
                "Every strain a different key / Unlocking what I'm meant to be 🔑🚪",
                "The clock moves slow, the mind moves fast / Present moment, vast and vast ⏰🌊",
                "Laughter echoes through the room / Dispelling every bit of gloom 🎭✨",
                "Nature's remedy, ancient and true / Making everything feel new 🏛️🌱",
                "Smoke signals to the universe / Composing my herbal verse 📡📝",
                "Sublime relaxation takes its hold / Worth its weight in green gold 💰🌿",
                "The ritual soothes my weary soul / Making broken pieces whole 🧩💚",
                "Perception shifts with every toke / Reality's just cosmic smoke 🔮💨",
                "In this space between the thoughts / Wisdom can't be bought or taught 🧘💭",
                "Floating on a sea of calm / Nature's perfect healing balm 🌊💚",
                "The plant speaks in silent ways / Guiding through the mental maze 🌿🧩",
                "Time becomes a fluid thing / As consciousness takes wing ⏰🦋",
                "Colors brighter, sounds more clear / In this elevated sphere 🎨🎵",
                "Sacred herb of peace and light / Making everything alright 🕊️💡",
                "Mind expands beyond the brain / Washing clear like gentle rain 🧠🌧️"
            ]
            
            couplet = random.choice(stoned_couplets)
            self.send_message(channel, couplet)
            
        elif command == "z6":
            # Countdown to December 4th, 2025 in Eastern time (seconds only)
            eastern_tz = ZoneInfo('America/New_York')
            target_date = datetime(2025, 12, 4, 0, 0, 0, tzinfo=eastern_tz)
            current_date = datetime.now(eastern_tz)
            
            if current_date >= target_date:
                self.send_message(channel, f"{nick}: December 4th, 2025 (ET) has already passed! 🎉")
            else:
                time_diff = target_date - current_date
                total_seconds = int(time_diff.total_seconds())
                self.send_message(channel, f"{nick}: {total_seconds:,} seconds until December 4th, 2025 (ET) ⏰")
        
        elif command == "time":
            # Countdown to December 4th, 2025
            target_date = datetime(2025, 12, 4, 0, 0, 0)
            current_date = datetime.now()
            
            if current_date >= target_date:
                self.send_message(channel, f"{nick}: December 4th, 2025 has already passed! 🎉")
            else:
                time_diff = target_date - current_date
                total_seconds = int(time_diff.total_seconds())
                
                # Toggle between detailed format (0) and seconds format (1)
                if self.time_format_mode == 0:
                    # Detailed format with months, weeks, days, hours, minutes, seconds
                    # Calculate months (approximate using 30.44 days per month)
                    months = int(total_seconds // (30.44 * 24 * 3600))
                    remaining_seconds = total_seconds % int(30.44 * 24 * 3600)
                    
                    # Calculate weeks
                    weeks = remaining_seconds // (7 * 24 * 3600)
                    remaining_seconds = remaining_seconds % (7 * 24 * 3600)
                    
                    # Calculate days
                    days = remaining_seconds // (24 * 3600)
                    remaining_seconds = remaining_seconds % (24 * 3600)
                    
                    # Calculate hours
                    hours = remaining_seconds // 3600
                    remaining_seconds = remaining_seconds % 3600
                    
                    # Calculate minutes
                    minutes = remaining_seconds // 60
                    seconds = remaining_seconds % 60
                    
                    # Build time string
                    time_parts = []
                    if months > 0:
                        time_parts.append(f"{months} month{'s' if months != 1 else ''}")
                    if weeks > 0:
                        time_parts.append(f"{weeks} week{'s' if weeks != 1 else ''}")
                    if days > 0:
                        time_parts.append(f"{days} day{'s' if days != 1 else ''}")
                    if hours > 0:
                        time_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
                    if minutes > 0:
                        time_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
                    if seconds > 0:
                        time_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
                    
                    if time_parts:
                        time_str = ", ".join(time_parts)
                        self.send_message(channel, f"{nick}: Time until December 4th, 2025: {time_str} ⏰")
                    else:
                        self.send_message(channel, f"{nick}: December 4th, 2025 is here! 🎉")
                else:
                    # Seconds format
                    self.send_message(channel, f"{nick}: Time until December 4th, 2025: {total_seconds:,} seconds ⏰")
                
                # Toggle format for next time
                self.time_format_mode = 1 - self.time_format_mode
                self.save_toke_data()
            
                
        elif command == "edible":
            # Edible command with funny weed wisdom - does NOT count as toke
            import random
            edible_phrases = [
                "Eating your way to enlightenment, one gummy at a time 🍬✨",
                "When smoking is too mainstream for your consciousness 🍪🧠",
                "The slow-release capsule of cosmic understanding ⏰💊",
                "Digestive system? More like dimension portal 🚪🌌",
                "Brownies: because adulting needs delicious distractions 🧁",
                "Metabolizing molecules of mysticism 🍫🔬",
                "Grandma's recipe meets quantum physics 👵⚛️",
                "Oral fixation meets orbital elevation 🛸",
                "The patient path to profound perspective 🧘",
                "When you want to get high AND satisfy your munchies simultaneously 🎯🍕",
                "Baked goods for getting baked: a delicious paradox 🥨♾️",
                "Confections for consciousness expansion 🍰🌠"
            ]
            
            phrase = random.choice(edible_phrases)
            self.send_message(channel, phrase)
            
        elif command == "blaze":
            # Special blaze command with sublime rotating quotes and tracking
            import random
            sublime_quotes = [
                "Ignite the sacred leaf and transcend the mundane 🔥🌿",
                "Through smoke we find clarity, through fire we find peace ✨💨",
                "The flame awakens what sleep has concealed 🕯️🧠",
                "Burning away illusions, one ember at a time 🔥💫",
                "In the glow of the cherry, wisdom blooms 🌸🔥",
                "Blazing trails through consciousness itself 🛤️✨",
                "Fire transforms the plant, smoke transforms the mind 🌿➡️☁️",
                "The ritual of flame, the sacrament of smoke 🕯️🙏",
                "Combustion unlocks the ancient secrets within 🔓🔥",
                "Lighting the path to inner worlds unexplored 🗺️💨",
                "When the herb meets fire, magic manifests 🪄🔥",
                "Smoke signals to higher dimensions 📡🌌",
                "The sacred flame purifies and elevates 🔥⬆️",
                "Burning bright, thinking deeper 💡🔥",
                "Through the blaze, we pierce the veil 🎭🔥",
                "Fire is the messenger, smoke is the message 📨💨",
                "Blazing into realms beyond ordinary perception 🚀🔥",
                "The alchemist's flame transmutes the mundane 🧪🔥",
                "Ignition of the spirit, liberation of the mind 🕊️🔥",
                "Where there's smoke, there's enlightenment 💡💨",
                "The eternal dance of flame and flower 💃🌸🔥",
                "Blazing bridges to the infinite 🌉♾️",
                "Fire speaks in languages older than words 🗣️🔥",
                "The glow that guides us inward 🧭✨",
                "Combustible contemplation, flammable philosophy 💭🔥",
                "Burning through barriers of perception 🚧🔥",
                "The flame that illuminates inner truth 💡🕯️",
                "Blazing with the fury of a thousand suns, yet peaceful 🌞😌",
                "Fire transforms matter, smoke transforms mind 🌿➡️🧠",
                "The ancient art of elevated existence 🎨🔥",
                "Kindle the consciousness, stoke the soul 🔥👤",
                "Where flame kisses flower, freedom follows 💋🌸🕊️",
                "The phoenix rises on clouds of smoke 🐦‍🔥☁️",
                "Blazing trails where others see only haze 🛤️🌫️",
                "Fire: nature's way of saying 'let's get deep' 🌲🔥",
                "Smoke sculptures of shifting consciousness ☁️🗿",
                "The ember glows with primordial wisdom 🔥🦕",
                "Burning questions lead to glowing answers 🔥❓➡️💡",
                "Through fire and smoke, we become un-woke... wait, MORE woke 🔥👁️",
                "The lighter's click: gateway to the infinite 🔓♾️",
                "Blaze on, space cadet, blaze on 🚀🔥",
                "When in doubt, blaze it out 💨💭",
                "The sacred lighter illuminates the way 🔥🛤️",
                "Combustion: because enlightenment shouldn't be boring 🔥🎉",
                "Fire cleanses, smoke ascends, mind transcends 🔥☁️🧠",
                "Blazing like the cosmos intended 🌌🔥",
                "The ceremonial ignition of infinite possibilities 🕯️♾️",
                "Flame on, tune in, blaze out 🔥📻💨",
                "Through the sacred blaze, we become unphased 🔥😎",
                "Let the herb burn, let the mind learn 🌿🔥🧠"
            ]
            
            current_time = time.time()
            
            # Update longest abstinence record if applicable
            if nick in self.toke_data:
                time_diff_seconds = int(current_time - self.toke_data[nick])
                if nick not in self.longest_abstinence or time_diff_seconds > self.longest_abstinence[nick]:
                    self.longest_abstinence[nick] = time_diff_seconds
            else:
                self.longest_abstinence[nick] = 0
            
            # Update toke count
            if nick not in self.toke_counts:
                self.toke_counts[nick] = 0
            self.toke_counts[nick] += 1
            
            # Add to toke history for gap tracking
            if nick not in self.toke_history:
                self.toke_history[nick] = []
            self.toke_history[nick].append(current_time)
            
            self.toke_data[nick] = current_time
            self.save_toke_data()
            
            # Send random sublime quote
            quote = random.choice(sublime_quotes)
            self.send_message(channel, quote)
            
        elif command == "pi":
            # Pi digit collection at 3:14 AM/PM
            user_datetime = self.get_user_datetime(nick)
            current_hour = user_datetime.hour
            current_minute = user_datetime.minute
            
            # Check if it's 3:14 AM (03:14) or 3:14 PM (15:14) in user's timezone
            is_pi_time = (current_hour == 3 or current_hour == 15) and current_minute == 14
            
            if not is_pi_time:
                # Show current progress even when not at pi time
                if nick in self.pi_progress:
                    digits = self.pi_progress[nick]
                    rounds = self.pi_rounds_won.get(nick, 0)
                    self.send_message(channel, f"{nick}: You have collected {digits} pi digits (base 64). Rounds won: {rounds}. Come back at 3:14 AM/PM! 🥧")
                else:
                    self.send_message(channel, f"{nick}: You haven't collected any pi digits yet! Use !pi at 3:14 AM/PM to start! 🥧")
                return
            
            # Initialize user's pi progress if needed
            if nick not in self.pi_progress:
                self.pi_progress[nick] = 0
            if nick not in self.pi_rounds_won:
                self.pi_rounds_won[nick] = 0
            
            # Get current digit count
            current_digits = self.pi_progress[nick]
            
            # Calculate which 60-digit chunk to show (0-59, 60-119, 120-179, etc.)
            chunk_index = current_digits // 60
            
            # Convert pi to base 64 (numeral system, not base64 encoding)
            # Pi in high precision decimal
            pi_decimal = "3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679821480865132823066470938446095505822317253594081284811174502841027019385211055596446229489549303819644288109756659334461284756482337867831652712019091456485669234603486104543266482133936072602491412737245870066063155881748815209209628292540917153643678925903600113305305488204665213841469519415116094330572703657595919530921861173819326117931051185480744623799627495673518857527248912279381830119491298336733624406566430860213949463952247371907021798609437027705392171762931767523846748184676694051320005681271452635608277857713427577896091736371787214684409012249534301465495853710507922796892589235420199561121290219608640344181598136297747713099605187072113499999983729780499510597317328160963185950244594553469083026425223082533446850352619311881710100031378387528865875332083814206171776691473035982534904287554687311595628638823537875937519577818577805321712268066130019278766111959092164201989"
            
            # Convert fractional part to base 64
            from decimal import Decimal, getcontext
            getcontext().prec = 2000
            
            decimal_part = pi_decimal.split('.')[1]
            frac = Decimal('0.' + decimal_part)
            
            # Generate enough base 64 digits
            max_needed = (chunk_index + 1) * 60
            pi_base64_digits = ['3', '.']
            
            for i in range(max_needed):
                frac *= 64
                digit = int(frac)
                if digit < 10:
                    pi_base64_digits.append(str(digit))
                elif digit < 36:
                    pi_base64_digits.append(chr(ord('A') + digit - 10))
                else:
                    pi_base64_digits.append(chr(ord('a') + digit - 36))
                frac -= digit
            
            pi_base64_full = ''.join(pi_base64_digits)
            
            # Extract the relevant 60-character chunk (including "3." for first chunk)
            if chunk_index == 0:
                # First chunk includes "3."
                pi_chunk = pi_base64_full[:62]  # "3." + 60 digits
            else:
                # Subsequent chunks: skip "3." and previous digits
                start_idx = 2 + (chunk_index * 60)
                end_idx = start_idx + 60
                if end_idx > len(pi_base64_full):
                    self.send_message(channel, f"{nick}: You've reached the limit of our pi digit database! 🎉 Total digits: {current_digits}, Rounds: {self.pi_rounds_won[nick]}")
                    return
                pi_chunk = pi_base64_full[start_idx:end_idx]
            
            # Update progress
            self.pi_progress[nick] += 60
            new_total = self.pi_progress[nick]
            
            # Check if they've reached 420 digits (or multiple of 420)
            if new_total % 420 == 0 and new_total > 0:
                self.pi_rounds_won[nick] += 1
                self.save_toke_data()
                self.send_message(channel, f"🎉🥧 {nick} WINS ROUND {self.pi_rounds_won[nick]}! 420 DIGITS! Next 60: {pi_chunk} 🥧🎉")
            else:
                self.save_toke_data()
                self.send_message(channel, f"🥧 {nick}: {pi_chunk} ({new_total}/420 | {420 - (new_total % 420)} to go)")
        
        elif command == "pi-show":
            # Show all collected base 64 pi digits
            if nick not in self.pi_progress or self.pi_progress[nick] == 0:
                self.send_message(channel, f"{nick}: You haven't collected any pi digits yet! Use !pi at 3:14 AM/PM to start! 🥧")
                return
            
            # Get user's total collected digits
            total_digits = self.pi_progress[nick]
            rounds = self.pi_rounds_won.get(nick, 0)
            
            # Convert pi to base 64 (numeral system, not base64 encoding)
            pi_decimal = "3.1415926535897932384626433832795028841971693993751058209749445923078164062862089986280348253421170679821480865132823066470938446095505822317253594081284811174502841027019385211055596446229489549303819644288109756659334461284756482337867831652712019091456485669234603486104543266482133936072602491412737245870066063155881748815209209628292540917153643678925903600113305305488204665213841469519415116094330572703657595919530921861173819326117931051185480744623799627495673518857527248912279381830119491298336733624406566430860213949463952247371907021798609437027705392171762931767523846748184676694051320005681271452635608277857713427577896091736371787214684409012249534301465495853710507922796892589235420199561121290219608640344181598136297747713099605187072113499999983729780499510597317328160963185950244594553469083026425223082533446850352619311881710100031378387528865875332083814206171776691473035982534904287554687311595628638823537875937519577818577805321712268066130019278766111959092164201989"
            
            from decimal import Decimal, getcontext
            getcontext().prec = 2000
            
            decimal_part = pi_decimal.split('.')[1]
            frac = Decimal('0.' + decimal_part)
            
            # Generate base 64 digits
            pi_base64_digits = ['3', '.']
            
            for i in range(total_digits):
                frac *= 64
                digit = int(frac)
                if digit < 10:
                    pi_base64_digits.append(str(digit))
                elif digit < 36:
                    pi_base64_digits.append(chr(ord('A') + digit - 10))
                else:
                    pi_base64_digits.append(chr(ord('a') + digit - 36))
                frac -= digit
            
            pi_base64 = ''.join(pi_base64_digits)
            
            # Send the results in one line (truncate if needed)
            max_display = 200  # Keep it short for single line
            if len(pi_base64) > max_display:
                display = pi_base64[:max_display] + "..."
            else:
                display = pi_base64
            self.send_message(channel, f"🥧 {nick}: {display} ({total_digits} digits | {rounds} rounds)")
        
        elif command == "t-break":
            # Show longest t-break (gap between tokes)
            if nick not in self.toke_history or len(self.toke_history[nick]) < 2:
                self.send_message(channel, f"{nick}: No t-break data yet! Use toke commands (!toke, !joint, !dab, etc) at least twice to track gaps. 🌿")
                return
            
            # Calculate all gaps between consecutive tokes
            toke_times = sorted(self.toke_history[nick])
            gaps = []
            for i in range(1, len(toke_times)):
                gap = toke_times[i] - toke_times[i-1]
                gaps.append(gap)
            
            # Find the longest gap
            longest_gap = max(gaps)
            
            # Get rating for longest gap
            stoner_rank = self.get_stoner_rank(int(longest_gap))
            
            # Format time
            days = int(longest_gap // 86400)
            hours = int((longest_gap % 86400) // 3600)
            minutes = int((longest_gap % 3600) // 60)
            seconds = int(longest_gap % 60)
            
            if days > 0:
                time_str = f"{days}d {hours}h {minutes}m {seconds}s"
            elif hours > 0:
                time_str = f"{hours}h {minutes}m {seconds}s"
            elif minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            
            # Send results
            self.send_message(channel, f"{nick}: Longest T-Break: {time_str} ({stoner_rank}) - {len(toke_times)} tokes tracked 🏆")
        
        elif command == "?":
            # Comprehensive help command covering all bot commands - all on one line
            self.send_message(channel, "🌿 CHR0N-BOT 🌿 !bud-zone [location]=timezone | !strain <name>=info | !stoned=poetry | !time=countdown | !z6=seconds | !blaze=toke+quote | !edible=wisdom | !pi=collect@3:14 | !pi-show=digits | !t-break=stats | !craps [bet|roll|status|cashout]=dice🎲 | !midi=compose🎵")
        
        elif command == "midi":
            # MIDI composition commands
            if not args:
                self.send_message(channel, f"{nick}: MIDI commands: !midi info | !midi play | !midi stop | !midi add <track> <note> <velocity> <start> <duration> | !midi tempo <bpm> | !midi track <name> | !midi instrument <track> <num> | !midi save | !midi clear 🎵")
                return
            
            subcommand = args[0].lower()
            
            if subcommand == "info":
                # Show composition info
                info = self.midi_manager.format_composition_info(nick)
                self.send_message(channel, f"{nick}: {info}")
            
            elif subcommand == "play":
                # Play user's composition
                comp = self.midi_manager.get_composition(nick)
                if comp.get_duration() == 0:
                    self.send_message(channel, f"{nick}: Your composition is empty! Add notes with: !midi add <track> <note> <velocity> <start> <duration> 🎵")
                    return
                
                if self.midi_manager.play(nick):
                    duration = comp.get_duration() * 60.0 / comp.tempo
                    self.send_message(channel, f"{nick}: 🎵 Playing '{comp.name}' (~{duration:.1f}s) - Notes will be logged! Use !midi stop to stop.")
                else:
                    self.send_message(channel, f"{nick}: Already playing! Use !midi stop first.")
            
            elif subcommand == "stop":
                # Stop playback
                self.midi_manager.stop()
                self.send_message(channel, f"{nick}: ⏹️ Playback stopped.")
            
            elif subcommand == "add":
                # Add a note: !midi add <track> <note> <velocity> <start> <duration>
                if len(args) < 6:
                    self.send_message(channel, f"{nick}: Usage: !midi add <track> <note> <velocity> <start> <duration> (Example: !midi add 0 60 100 0 1)")
                    return
                
                try:
                    track = int(args[1])
                    note = int(args[2])
                    velocity = int(args[3])
                    start = float(args[4])
                    duration = float(args[5])
                    
                    comp = self.midi_manager.get_composition(nick)
                    if track >= len(comp.tracks):
                        self.send_message(channel, f"{nick}: Track {track} doesn't exist! Use !midi track to add more tracks.")
                        return
                    
                    comp.add_note(track, note, velocity, start, duration)
                    self.midi_manager.save_composition(nick)
                    note_name = self.midi_manager.player._note_to_name(note)
                    self.send_message(channel, f"{nick}: ✅ Added {note_name} (MIDI {note}) to track {track} at beat {start} for {duration} beats")
                except ValueError:
                    self.send_message(channel, f"{nick}: Invalid parameters! Use numbers only.")
            
            elif subcommand == "tempo":
                # Set tempo: !midi tempo <bpm>
                if len(args) < 2:
                    self.send_message(channel, f"{nick}: Usage: !midi tempo <bpm> (Example: !midi tempo 120)")
                    return
                
                try:
                    tempo = int(args[1])
                    if tempo < 20 or tempo > 300:
                        self.send_message(channel, f"{nick}: Tempo must be between 20 and 300 BPM")
                        return
                    
                    comp = self.midi_manager.get_composition(nick)
                    comp.tempo = tempo
                    self.midi_manager.save_composition(nick)
                    self.send_message(channel, f"{nick}: ✅ Tempo set to {tempo} BPM")
                except ValueError:
                    self.send_message(channel, f"{nick}: Invalid tempo! Use a number.")
            
            elif subcommand == "track":
                # Add a new track: !midi track <name>
                if len(args) < 2:
                    self.send_message(channel, f"{nick}: Usage: !midi track <name> (Example: !midi track Bass)")
                    return
                
                track_name = " ".join(args[1:])
                comp = self.midi_manager.get_composition(nick)
                track_idx = comp.add_track(track_name)
                self.midi_manager.save_composition(nick)
                self.send_message(channel, f"{nick}: ✅ Added track {track_idx}: '{track_name}'")
            
            elif subcommand == "instrument":
                # Set track instrument: !midi instrument <track> <instrument_num>
                if len(args) < 3:
                    self.send_message(channel, f"{nick}: Usage: !midi instrument <track> <num> (Example: !midi instrument 0 33 for bass)")
                    return
                
                try:
                    track = int(args[1])
                    instrument = int(args[2])
                    
                    comp = self.midi_manager.get_composition(nick)
                    if track >= len(comp.tracks):
                        self.send_message(channel, f"{nick}: Track {track} doesn't exist!")
                        return
                    
                    comp.set_instrument(track, instrument)
                    self.midi_manager.save_composition(nick)
                    self.send_message(channel, f"{nick}: ✅ Track {track} instrument set to {instrument}")
                except ValueError:
                    self.send_message(channel, f"{nick}: Invalid parameters! Use numbers only.")
            
            elif subcommand == "save":
                # Save composition
                if self.midi_manager.save_composition(nick):
                    self.send_message(channel, f"{nick}: ✅ Composition saved!")
                else:
                    self.send_message(channel, f"{nick}: ❌ Failed to save composition.")
            
            elif subcommand == "clear":
                # Clear composition and start fresh
                from midi_player import MidiComposition
                self.midi_manager.compositions[nick] = MidiComposition(f"{nick}'s composition")
                self.midi_manager.save_composition(nick)
                self.send_message(channel, f"{nick}: ✅ Composition cleared! Start fresh with !midi add")
            
            else:
                self.send_message(channel, f"{nick}: Unknown MIDI command. Use !midi for help.")
        
        elif command == "craps":
            # Craps dice game with betting
            import random
            
            # Initialize player if new
            if nick not in self.craps_games:
                self.craps_games[nick] = {'point': None, 'chips': 100, 'bet': 0, 'wins': 0, 'losses': 0}
            
            player = self.craps_games[nick]
            
            if not args:
                # Show help
                self.send_message(channel, f"{nick}: 🎲 !craps bet <amount> | !craps roll | !craps status | !craps cashout 🎲")
                return
            
            subcommand = args[0].lower()
            
            if subcommand == "status":
                self.send_message(channel, f"🎲 {nick}: {player['chips']} chips | Point: {player['point'] or 'None'} | W/L: {player['wins']}/{player['losses']} | Bet: {player['bet']}")
            
            elif subcommand == "bet":
                if len(args) < 2:
                    self.send_message(channel, f"{nick}: Usage: !craps bet <amount> (Min: 1, Max: all)")
                    return
                
                if player['bet'] > 0:
                    self.send_message(channel, f"{nick}: You already have a bet of {player['bet']} chips! Roll or cashout first.")
                    return
                
                bet_amount = args[1].lower()
                if bet_amount == "all":
                    bet = player['chips']
                else:
                    try:
                        bet = int(bet_amount)
                    except ValueError:
                        self.send_message(channel, f"{nick}: Invalid bet amount. Use a number or 'all'.")
                        return
                
                if bet < 1:
                    self.send_message(channel, f"{nick}: Minimum bet is 1 chip.")
                    return
                
                if bet > player['chips']:
                    self.send_message(channel, f"{nick}: You only have {player['chips']} chips!")
                    return
                
                player['bet'] = bet
                player['chips'] -= bet
                self.save_toke_data()
                self.send_message(channel, f"🎲 {nick}: Bet {bet} chips! Roll with !craps roll. Remaining: {player['chips']} chips")
            
            elif subcommand == "roll":
                if player['bet'] == 0:
                    self.send_message(channel, f"{nick}: Place a bet first with !craps bet <amount>")
                    return
                
                # Roll two dice
                die1 = random.randint(1, 6)
                die2 = random.randint(1, 6)
                total = die1 + die2
                
                dice_emoji = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
                dice_display = f"{dice_emoji[die1]} {dice_emoji[die2]}"
                
                if player['point'] is None:
                    # Come-out roll
                    if total in [7, 11]:
                        # Natural - win
                        winnings = player['bet'] * 2
                        player['chips'] += winnings
                        player['wins'] += 1
                        player['bet'] = 0
                        self.save_toke_data()
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | NATURAL! WIN! +{winnings} chips | Total: {player['chips']} 🎉")
                    elif total in [2, 3, 12]:
                        # Craps - lose
                        player['losses'] += 1
                        player['bet'] = 0
                        self.save_toke_data()
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | CRAPS! Lost bet. | Total: {player['chips']} 💀")
                    else:
                        # Point established
                        player['point'] = total
                        self.save_toke_data()
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | POINT SET! Roll {total} to win, 7 to lose. Roll again!")
                else:
                    # Point is set
                    if total == player['point']:
                        # Made the point - win
                        winnings = player['bet'] * 2
                        player['chips'] += winnings
                        player['wins'] += 1
                        player['point'] = None
                        player['bet'] = 0
                        self.save_toke_data()
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | POINT MADE! WIN! +{winnings} chips | Total: {player['chips']} 🎉")
                    elif total == 7:
                        # Seven out - lose
                        player['losses'] += 1
                        player['point'] = None
                        player['bet'] = 0
                        self.save_toke_data()
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | SEVEN OUT! Lost bet. | Total: {player['chips']} 💀")
                    else:
                        # Keep rolling
                        self.send_message(channel, f"🎲 {nick}: {dice_display} = {total} | Point: {player['point']} | Keep rolling!")
            
            elif subcommand == "cashout":
                if player['bet'] > 0:
                    # Return bet to chips
                    player['chips'] += player['bet']
                    returned_bet = player['bet']
                    player['bet'] = 0
                    player['point'] = None
                    self.save_toke_data()
                    self.send_message(channel, f"🎲 {nick}: Cashed out! Returned {returned_bet} chips. Total: {player['chips']} chips")
                else:
                    self.send_message(channel, f"🎲 {nick}: No active bet to cash out. Total: {player['chips']} chips")
            
            else:
                self.send_message(channel, f"{nick}: Unknown craps command. Use !craps for help.")
    
    def handle_private_command(self, parsed_msg):
        """Handle private message commands (only !bud-zone)"""
        if not parsed_msg['message'].startswith(self.command_prefix):
            return
            
        command_parts = parsed_msg['message'][1:].split()
        command = command_parts[0].lower()
        args = command_parts[1:] if len(command_parts) > 1 else []
        
        nick = parsed_msg['nick']
        
        # Only allow !bud-zone command in private messages
        if command == "bud-zone":
            if not args:
                # Show current timezone
                if nick in self.user_timezones:
                    current_tz = self.user_timezones[nick]
                    user_dt = self.get_user_datetime(nick)
                    self.send_message(nick, f"Your bud-zone is set to {current_tz} (currently {user_dt.strftime('%I:%M %p %Z')} 🌍🌿)")
                else:
                    self.send_message(nick, f"You haven't set a bud-zone yet! Use: !bud-zone <city state country> 🌍🌿")
            else:
                # Set timezone based on location
                location_str = " ".join(args)
                timezone = self.get_timezone_from_location(args)
                
                if timezone:
                    self.user_timezones[nick] = timezone
                    self.save_toke_data()
                    user_dt = self.get_user_datetime(nick)
                    self.send_message(nick, f"Bud-zone set to {location_str} ({timezone}) - currently {user_dt.strftime('%I:%M %p %Z')} 🌍🌿")
                    self.send_message(nick, f"Your 4:20 times will now be based on {location_str} timezone! 🕐🌿")
                else:
                    self.send_message(nick, f"Sorry, couldn't find timezone for '{location_str}'. Try: city, state, country (e.g., 'Los Angeles CA', 'London UK', 'Tokyo Japan') 🌍🌿")
        else:
            # Let them know only !bud-zone works in private messages
            self.send_message(nick, f"Only !bud-zone can be used in private messages. Use commands in the channel for other features! 🌿")
            
    def start_420_monitor(self):
        """Start background thread to monitor for 4:20 times"""
        def check_420_times():
            while self.connected:
                try:
                    current_time = time.time()
                    
                    # Check each user with a timezone
                    for user_nick, timezone_str in list(self.user_timezones.items()):
                        try:
                            user_tz = ZoneInfo(timezone_str)
                            user_datetime = datetime.now(user_tz)
                            user_hour = user_datetime.hour
                            user_minute = user_datetime.minute
                            
                            # Check if it's 4:20 AM or PM
                            is_420 = (user_hour == 4 or user_hour == 16) and user_minute == 20
                            
                            if is_420:
                                # Check if we've already awarded for this 4:20 window
                                if user_nick not in self.active_420_windows:
                                    # New 4:20 window - award point
                                    if user_nick not in self.auto_420_points:
                                        self.auto_420_points[user_nick] = 0
                                    self.auto_420_points[user_nick] += 1
                                    self.active_420_windows[user_nick] = current_time
                                    self.save_toke_data()
                                    
                                    period = "AM" if user_hour == 4 else "PM"
                                    for channel in self.channels:
                                        self.send_message(channel, f"🕐 It's 4:20 {period} in {user_nick}'s bud-zone! They get +1 point! Use !churchbong {user_nick} to get a point too! 🌿")
                            else:
                                # Not 4:20, clear the window if it exists
                                if user_nick in self.active_420_windows:
                                    del self.active_420_windows[user_nick]
                        
                        except Exception as e:
                            self.logger.error(f"Error checking 4:20 for {user_nick}: {e}")
                    
                    # Sleep for 30 seconds before next check
                    time.sleep(30)
                    
                except Exception as e:
                    self.logger.error(f"Error in 420 monitor: {e}")
                    time.sleep(30)
        
        self.timezone_check_thread = threading.Thread(target=check_420_times, daemon=True)
        self.timezone_check_thread.start()
        self.logger.info("Started 4:20 monitoring thread")
    
    def listen(self):
        """Main message listening loop"""
        buffer = ""
        self.start_time = time.time()
        
        # Start the 4:20 monitoring thread
        # self.start_420_monitor()  # Disabled automatic 4:20 announcements
        
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8', errors='ignore')
                if not data:
                    break
                    
                buffer += data
                lines = buffer.split('\r\n')
                buffer = lines[-1]  # Keep incomplete line in buffer
                
                for line in lines[:-1]:
                    if line:
                        self.logger.debug(f"RECV: {line}")
                        
                        # Handle PING
                        if line.startswith("PING"):
                            self.handle_ping(line)
                            continue
                            
                        # Parse message
                        parsed_msg = self.parse_message(line)
                        if not parsed_msg:
                            continue
                            
                        # Handle successful connection
                        if parsed_msg['command'] == '001':  # Welcome message
                            # Handle NickServ registration/identification
                            if self.nickserv_register and not self.nickserv_registered:
                                if self.nickserv_password and self.nickserv_email:
                                    self.logger.info("Attempting to register with NickServ...")
                                    self.send_raw(f"PRIVMSG NickServ :REGISTER {self.nickserv_password} {self.nickserv_email}")
                                    self.nickserv_registered = True
                                    time.sleep(2)  # Wait for registration response
                            elif self.nickserv_password and not self.nickserv_register:
                                # Just identify if already registered
                                self.logger.info("Identifying with NickServ...")
                                self.send_raw(f"PRIVMSG NickServ :IDENTIFY {self.nickserv_password}")
                                time.sleep(2)  # Wait for identification
                            
                            for channel in self.channels:
                                time.sleep(1)  # Rate limiting
                                self.join_channel(channel)
                                
                        # Handle channel messages and private messages
                        elif parsed_msg['command'] == 'PRIVMSG':
                            if parsed_msg['target'].startswith('#'):
                                # Channel message
                                self.handle_command(parsed_msg)
                            elif parsed_msg['target'] == self.nickname:
                                # Private message - handle only !bud-zone command
                                self.handle_private_command(parsed_msg)
                                
            except Exception as e:
                self.logger.error(f"Error in listen loop: {e}")
                break
                
        self.disconnect()
        
    def disconnect(self):
        """Disconnect from IRC server"""
        if self.socket:
            self.send_raw("QUIT :Bot shutting down")
            self.socket.close()
            self.connected = False
            self.logger.info("Disconnected from server")
            
    def run(self):
        """Main bot run method"""
        self.logger.info("Starting IRC bot...")
        
        if self.connect():
            try:
                self.listen()
            except KeyboardInterrupt:
                self.logger.info("Received interrupt signal")
            finally:
                self.disconnect()
        else:
            self.logger.error("Failed to connect to server")

def main():
    bot = IRCBot()
    bot.run()

if __name__ == "__main__":
    main()