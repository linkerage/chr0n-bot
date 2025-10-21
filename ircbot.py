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

class IRCBot:
    def __init__(self, config_file="config.json"):
        self.load_config(config_file)
        self.socket = None
        self.connected = False
        self.setup_logging()
        self.load_toke_data()
        
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
                "channels": ["#gentoo-weed"],
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
        
    def setup_logging(self):
        """Setup logging for the bot"""
        logging.basicConfig(
            level=logging.INFO,
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
                else:
                    # Old format, migrate
                    self.toke_data = data
                    self.tb_enabled = {}
                    self.toke_counts = {}
                    self.longest_abstinence = {}
                    self.user_timezones = {}
                    self.precision_timing = {}
        except (FileNotFoundError, EOFError):
            self.toke_data = {}  # {user: last_toke_timestamp}
            self.tb_enabled = {}  # {user: True/False}
            self.toke_counts = {}  # {user: total_tokes}
            self.longest_abstinence = {}  # {user: longest_seconds}
            self.user_timezones = {}  # {user: timezone_string}
            self.precision_timing = {}  # {user: {'last_420_time': timestamp, 'perfect_cycles': int, 'total_420s': int, 'best_precision': seconds_off}}
            
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
                    'precision_timing': self.precision_timing
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
        
        # Rating system with emojis (highest to lowest)
        time_ratings = []
        if years > 0:
            decades = years // 10
            remaining_years = years % 10
            if decades > 0:
                time_ratings.append(f"{decades} decade{'s' if decades != 1 else ''} 👑🏆 (LEGENDARY)")
            if remaining_years > 0:
                time_ratings.append(f"{remaining_years} year{'s' if remaining_years != 1 else ''} 🏆 (EPIC)")
        if months > 0:
            time_ratings.append(f"{months} month{'s' if months != 1 else ''} 🥇 (MASTER)")
        if weeks > 0:
            time_ratings.append(f"{weeks} week{'s' if weeks != 1 else ''} 🥈 (EXPERT)")
        if days > 0:
            time_ratings.append(f"{days} day{'s' if days != 1 else ''} 🥉 (SKILLED)")
        if hours > 0:
            time_ratings.append(f"{hours} hour{'s' if hours != 1 else ''} ⭐ (DECENT)")
        if minutes > 0:
            time_ratings.append(f"{minutes} minute{'s' if minutes != 1 else ''} 💫 (BASIC)")
        if seconds > 0 or len(time_ratings) == 0:
            time_ratings.append(f"{seconds} second{'s' if seconds != 1 else ''} 🔹 (ROOKIE)")
        
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
        
        time_breakdown = " + ".join(time_ratings)
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
        
        channel = parsed_msg['target']
        nick = parsed_msg['nick']
        
        # Bot commands
        if command == "help":
            self.send_message(channel, f"{nick}: Available commands: !help, !ping, !about, !uptime, !gentoo, !time, !bud-zone, !rankings, !churchbong, !toke, !pass, !joint, !dab, !blunt, !bong, !vape, !doombong, !olddoombong, !kylebong, !blaze")
            
        elif command == "ping":
            self.send_message(channel, f"{nick}: Pong!")
            
        elif command == "about":
            self.send_message(channel, f"{nick}: I'm a bot for {channel}. Running on Python 3!")
            
        elif command == "uptime":
            uptime = int(time.time() - self.start_time)
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            seconds = uptime % 60
            self.send_message(channel, f"{nick}: Uptime: {hours}h {minutes}m {seconds}s")
            
        elif command == "gentoo":
            responses = [
                "Gentoo: The choice of a GNU generation!",
                "emerge --world && profit",
                "USE flags are life!",
                "Compile everything from source!",
                "~x86 master race"
            ]
            import random
            self.send_message(channel, f"{nick}: {random.choice(responses)}")
            
        elif command == "bud-zone":
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
                    self.send_message(channel, f"{nick}: Bud-zone set to {location_str} ({timezone}) - currently {user_dt.strftime('%I:%M %p %Z')} 🌍🌿")
                    self.send_message(channel, f"Your 4:20 times will now be based on {location_str} timezone! 🕐🌿")
                else:
                    self.send_message(channel, f"{nick}: Sorry, couldn't find timezone for '{location_str}'. Try: city, state, country (e.g., 'Los Angeles CA', 'London UK', 'Tokyo Japan') 🌍🌿")
            
        elif command == "rankings":
            # Show abstinence leaderboard - longest time since last toke at top
            current_time = time.time()
            
            # Calculate current abstinence times for all users
            user_abstinence = []
            for user, last_toke in self.toke_data.items():
                time_abstinent = int(current_time - last_toke)
                user_abstinence.append((user, time_abstinent))
            
            if not user_abstinence:
                self.send_message(channel, "🏆 No one has toked yet! Be the first to use !churchbong 🌿")
                return
            
            # Sort by abstinence time (longest first)
            user_abstinence.sort(key=lambda x: x[1], reverse=True)
            
            # Show top rankings
            self.send_message(channel, "🏆 ABSTINENCE LEADERBOARD - Longest Time Since Last Toke 🌿")
            
            for i, (user, seconds_abstinent) in enumerate(user_abstinence[:10], 1):
                # Get abstinence rating
                time_breakdown, overall_rating = self.get_abstinence_rating(seconds_abstinent)
                
                # Format time display
                days = int(seconds_abstinent // 86400)
                hours = int((seconds_abstinent % 86400) // 3600) 
                minutes = int((seconds_abstinent % 3600) // 60)
                seconds = int(seconds_abstinent % 60)
                
                if days > 0:
                    time_str = f"{days}d {hours}h {minutes}m"
                elif hours > 0:
                    time_str = f"{hours}h {minutes}m"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                
                # Rank emojis
                if i == 1:
                    rank_emoji = "🥇"  # Gold medal
                elif i == 2:
                    rank_emoji = "🥈"  # Silver medal
                elif i == 3:
                    rank_emoji = "🥉"  # Bronze medal
                else:
                    rank_emoji = f"{i}."
                
                # Get humorous stoner ranking based on abstinence time
                simple_rating = self.get_stoner_rank(seconds_abstinent)
                
                self.send_message(channel, f"{rank_emoji} {user}: {time_str} ({simple_rating})")
            
            # Show total tracked users
            total_users = len(user_abstinence)
            if total_users > 10:
                self.send_message(channel, f"... and {total_users - 10} more tokers! Use !churchbong to join the rankings! 🌿")
            
        elif command == "time":
            # Countdown to December 4th, 2025
            target_date = datetime(2025, 12, 4, 0, 0, 0)
            current_date = datetime.now()
            
            if current_date >= target_date:
                self.send_message(channel, f"{nick}: December 4th, 2025 has already passed! 🎉")
            else:
                time_diff = target_date - current_date
                
                # Calculate total components
                total_seconds = int(time_diff.total_seconds())
                
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
            
        elif command == "churchbong":
            # Works with or without "420" argument
            current_time = time.time()
            user_datetime = self.get_user_datetime(nick)
            current_hour = user_datetime.hour
            current_minute = user_datetime.minute
            
            # Check if it's 4:20 AM (04:20) or 4:20 PM (16:20) in user's timezone for detailed analysis
            is_420_time = (current_hour == 4 or current_hour == 16) and current_minute == 20
            
            if nick in self.toke_data:
                # Calculate time since last toke
                last_toke = self.toke_data[nick]
                time_diff_seconds = int(current_time - last_toke)
                
                # Update longest abstinence record
                if nick not in self.longest_abstinence or time_diff_seconds > self.longest_abstinence[nick]:
                    self.longest_abstinence[nick] = time_diff_seconds
                
                # Simple time display
                days = int(time_diff_seconds // 86400)
                hours = int((time_diff_seconds % 86400) // 3600) 
                minutes = int((time_diff_seconds % 3600) // 60)
                seconds = int(time_diff_seconds % 60)
                
                if days > 0:
                    time_str = f"{days}d {hours}h {minutes}m {seconds}s"
                elif hours > 0:
                    time_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                
                # Calculate current ranking position
                current_time_temp = time.time()
                user_position = 1
                for other_user, other_last_toke in self.toke_data.items():
                    if other_user != nick:
                        other_abstinence = int(current_time_temp - other_last_toke)
                        if other_abstinence > time_diff_seconds:
                            user_position += 1
                
                total_users = len(self.toke_data)
                stoner_rank = self.get_stoner_rank(time_diff_seconds)
                rank_info = f"(#{user_position}/{total_users}: {stoner_rank})"
                
                self.send_message(channel, f"{nick}: Time since last toked: {time_str} {rank_info} 🔔💨")
                
                # Only show detailed rating system at 4:20 AM/PM
                if is_420_time:
                    # Calculate precision timing for this 4:20 attempt
                    seconds_off, is_perfect_cycle, precision_rank, timing_data = self.calculate_precision_score(nick, user_datetime, current_time)
                    
                    # Show precision timing first (most important at 4:20)
                    if seconds_off == 0:
                        self.send_message(channel, f"🕐 PERFECT 4:20:00 HIT! {precision_rank} 🎆")
                    else:
                        self.send_message(channel, f"🕐 4:20 PRECISION: {seconds_off}s off perfect timing")
                    
                    self.send_message(channel, f"🎩 TIMING RANK: {precision_rank}")
                    
                    if is_perfect_cycle:
                        self.send_message(channel, f"🔄 PERFECT 12H CYCLE MAINTAINED! Streak: {timing_data['cycle_streak']} ⚡")
                    
                    cycle_info = f"Cycles: {timing_data['perfect_cycles']} | Streak: {timing_data['cycle_streak']} | Total 4:20s: {timing_data['total_420s']}"
                    best_precision = timing_data['best_precision']
                    if best_precision == float('inf'):
                        best_precision = seconds_off
                    self.send_message(channel, f"📊 PRECISION STATS: {cycle_info} | Best: {best_precision}s off")
                    
                    # Get rating breakdown
                    time_breakdown, overall_rating = self.get_abstinence_rating(time_diff_seconds)
                    # Get longest record breakdown
                    longest_breakdown, longest_rating = self.get_abstinence_rating(self.longest_abstinence[nick])
                    
                    self.send_message(channel, f"📊 CURRENT RATING: {time_breakdown}")
                    self.send_message(channel, f"🎖️ STATUS: {overall_rating}")
                    self.send_message(channel, f"🏆 LONGEST RECORD: {longest_breakdown}")
                    
                    # Update toke count
                    if nick not in self.toke_counts:
                        self.toke_counts[nick] = 0
                    self.toke_counts[nick] += 1
                    
                    # Show toke count only at 4:20
                    self.send_message(channel, f"🔢 TOTAL TOKES: {self.toke_counts[nick]}")
                else:
                    # Regular churchbong - just update counts silently
                    if nick not in self.toke_counts:
                        self.toke_counts[nick] = 0
                    self.toke_counts[nick] += 1
                    
            else:
                self.send_message(channel, f"{nick}: First churchbong recorded! May the sacred smoke guide you. 🔔💨")
                self.longest_abstinence[nick] = 0
                
                # Initialize toke count
                if nick not in self.toke_counts:
                    self.toke_counts[nick] = 0
                self.toke_counts[nick] += 1
                
                # Show toke count only at 4:20 for first time users too
                if is_420_time:
                    self.send_message(channel, f"🔢 TOTAL TOKES: {self.toke_counts[nick]}")
            
            # Update user's last toke time
            self.toke_data[nick] = current_time
            self.save_toke_data()
            
            # If they typed "420", add a random 420 fact or special quote during 4:20 times
            if args and args[0] == "420":
                user_datetime_420 = self.get_user_datetime(nick)
                current_hour = user_datetime_420.hour
                current_minute = user_datetime_420.minute
                
                # Check if it's 4:20 AM (04:20) or 4:20 PM (16:20) in user's timezone
                if (current_hour == 4 or current_hour == 16) and current_minute == 20:
                    # Calculate days since last toke for quote selection
                    days_abstinent = 0
                    if nick in self.toke_data:
                        last_toke = self.toke_data[nick]
                        time_since_last = current_time - last_toke
                        days_abstinent = int(time_since_last // 86400)
                    
                    # Famous quotes adapted for weed, ordered chronologically (oldest to newest)
                    # The longer you abstain, the more ancient the wisdom becomes
                    chronological_weed_quotes = [
                        # Ancient Era (7+ days) - Julius Caesar ~50 BC
                        "\"I came, I saw, I conquered... this entire bag of Cheetos\" - Julius Blazer (50 BC) 🏛️",
                        # Renaissance (6-7 days) - Shakespeare ~1600
                        "\"To toke, or not to toke, that is the question\" - William Smokespeare (1603) 🎭",
                        # Enlightenment (5-6 days) - Edmund Burke ~1770
                        "\"The only thing necessary for the triumph of evil is for good men to run out of weed\" - Edmund Burked (1770) 📜",
                        # American Revolution (4-5 days) - Patrick Henry 1775
                        "\"Give me liberty, or give me death... but preferably give me more cannabis\" - Patrick Henry Hemp (1775) 🗽",
                        # Poetry Era (3-4 days) - Robert Frost ~1920
                        "\"Two roads diverged in a wood, and I took the one that led to the dispensary\" - Robert Frostbite (1920) 📖",
                        # Great Depression (2-3 days) - FDR 1933
                        "\"The only thing we have to fear is fear itself... and running out of weed\" - Franklin D. Roachevelt (1933) 🎩",
                        # Civil Rights Era (1-2 days) - JFK 1961
                        "\"Ask not what your dealer can do for you, ask what you can do for your dealer\" - John F. Kannedy (1961) 🌟",
                        # Civil Rights Era (1-2 days) - MLK 1963
                        "\"I have a dream... that one day all buds will be judged not by the color of their strain, but by the content of their THC\" - Martin Luther Kief (1963) ✊",
                        # Civil Rights Era alt (1-2 days) - MLK 1967
                        "\"Darkness cannot drive out darkness; only light can do that. Hate cannot drive out hate; only weed can do that\" - Martin Luther Kief Jr. (1967) ☮️",
                        # Space Age (1 day) - Neil Armstrong 1969
                        "\"That's one small toke for man, one giant bong rip for mankind\" - Neil Strongarm (1969) 🚀",
                        # Boxing Era (< 1 day) - Muhammad Ali ~1974
                        "\"Float like a butterfly, sting like a bee, smoke like a chimney\" - Muhammad Highli (1974) 🥊",
                        # Cold War (< 1 day) - Reagan 1987
                        "\"Mr. Gorbachev, tear down this wall... and pass that joint\" - Ronald Reefer (1987) 🧱"
                    ]
                    
                    # Select quote based on abstinence time (longer = older quotes)
                    if days_abstinent >= 7:
                        quote_index = 0  # Ancient (Julius Caesar)
                    elif days_abstinent >= 6:
                        quote_index = 1  # Renaissance (Shakespeare)
                    elif days_abstinent >= 5:
                        quote_index = 2  # Enlightenment (Burke)
                    elif days_abstinent >= 4:
                        quote_index = 3  # American Revolution (Henry)
                    elif days_abstinent >= 3:
                        quote_index = 4  # Poetry Era (Frost)
                    elif days_abstinent >= 2:
                        quote_index = 5  # Great Depression (FDR)
                    elif days_abstinent >= 1:
                        # Civil Rights Era - randomly choose from 3 quotes
                        import random
                        quote_index = random.choice([6, 7, 8])  # JFK, MLK1, MLK2
                    else:
                        # Recent era (< 1 day) - randomly choose from newest 3
                        import random
                        quote_index = random.choice([9, 10, 11])  # Armstrong, Ali, Reagan
                    
                    quote = chronological_weed_quotes[quote_index]
                    
                    # Calculate detailed time breakdown with ratings
                    if nick in self.toke_data:
                        last_toke = self.toke_data[nick]
                        total_seconds_since = int(current_time - last_toke)
                        
                        # Calculate all time units
                        years = total_seconds_since // (365.25 * 24 * 3600)
                        remaining = total_seconds_since % int(365.25 * 24 * 3600)
                        
                        months = remaining // int(30.44 * 24 * 3600)
                        remaining = remaining % int(30.44 * 24 * 3600)
                        
                        weeks = remaining // (7 * 24 * 3600)
                        remaining = remaining % (7 * 24 * 3600)
                        
                        days = remaining // (24 * 3600)
                        remaining = remaining % (24 * 3600)
                        
                        hours = remaining // 3600
                        remaining = remaining % 3600
                        
                        minutes = remaining // 60
                        seconds = remaining % 60
                        
                        # Rating system with emojis (highest to lowest)
                        time_ratings = []
                        if years > 0:
                            decades = years // 10
                            remaining_years = years % 10
                            if decades > 0:
                                time_ratings.append(f"{decades} decade{'s' if decades != 1 else ''} 👑🏆 (LEGENDARY)")
                            if remaining_years > 0:
                                time_ratings.append(f"{remaining_years} year{'s' if remaining_years != 1 else ''} 🏆 (EPIC)")
                        if months > 0:
                            time_ratings.append(f"{months} month{'s' if months != 1 else ''} 🥇 (MASTER)")
                        if weeks > 0:
                            time_ratings.append(f"{weeks} week{'s' if weeks != 1 else ''} 🥈 (EXPERT)")
                        if days > 0:
                            time_ratings.append(f"{days} day{'s' if days != 1 else ''} 🥉 (SKILLED)")
                        if hours > 0:
                            time_ratings.append(f"{hours} hour{'s' if hours != 1 else ''} ⭐ (DECENT)")
                        if minutes > 0:
                            time_ratings.append(f"{minutes} minute{'s' if minutes != 1 else ''} 💫 (BASIC)")
                        if seconds > 0 or len(time_ratings) == 0:
                            time_ratings.append(f"{seconds} second{'s' if seconds != 1 else ''} 🔹 (ROOKIE)")
                        
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
                        
                        time_breakdown = " + ".join(time_ratings)
                        
                        # Send the wisdom quote
                        self.send_message(channel, f"🕐 4:20 ANCIENT WISDOM: {quote}")
                        # Send the detailed rating breakdown
                        self.send_message(channel, f"📊 ABSTINENCE ANALYSIS: {time_breakdown}")
                        self.send_message(channel, f"🎖️ OVERALL RATING: {overall_rating}")
                    else:
                        # First time user
                        self.send_message(channel, f"🕐 4:20 ANCIENT WISDOM: {quote}")
                        self.send_message(channel, f"📊 ABSTINENCE ANALYSIS: First churchbong! 🔹 (ROOKIE STATUS)")
                else:
                    # Regular 420 facts for non-4:20 times
                    facts_420 = [
                        "4:20 PM is Adolf Hitler's birthday - April 20th, 1889. Coincidence? Most say yes.",
                        "420 is police code for marijuana smoking in progress (actually a myth - it's not real police code).",
                        "4:20 PM was when a group of California high schoolers called 'The Waldos' would meet to smoke in 1971.",
                        "April 20th (4/20) is considered the unofficial holiday for cannabis culture worldwide.",
                        "The number 420 appears in Bob Dylan's song 'Rainy Day Women #12 & 35' (12 × 35 = 420).",
                        "In Las Vegas, many hotel rooms numbered 420 have been stolen so often they're now numbered 419+1.",
                        "The first 420 celebration was held at San Rafael High School in California in 1971.",
                        "420 is the sum of 4:20 PM in minutes (16:20 = 16×60+20 = 980... wait, that's not right).",
                        "Cannabis has 420 chemical compounds (actually it has over 480, but close enough).",
                        "The Grateful Dead's official fan club address was 420 Natoma Street in San Francisco.",
                        "Highway 420 in Canada was renamed because the signs kept getting stolen.",
                        "420 BC was supposedly when the ancient Greeks first discovered hemp cultivation.",
                        "The code H.R.420 was used for multiple cannabis legalization bills in the U.S. Congress."
                    ]
                    import random
                    fact = random.choice(facts_420)
                    self.send_message(channel, f"420 Fact: {fact}")
                
        elif command in ["toke", "pass", "joint", "dab", "blunt", "bong", "vape", "doombong", "olddoombong", "kylebong"]:
            # Silent toke tracking - just record timestamp without response
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
            
            self.toke_data[nick] = current_time
            self.save_toke_data()
            # No message sent - silent tracking
            
        elif command == "blaze":
            # Special blaze command with message and tracking
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
            
            self.toke_data[nick] = current_time
            self.save_toke_data()
            self.send_message(channel, "Fire is going to get you higher, blaze it till you phaze it.")
            
    def listen(self):
        """Main message listening loop"""
        buffer = ""
        self.start_time = time.time()
        
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
                            for channel in self.channels:
                                time.sleep(1)  # Rate limiting
                                self.join_channel(channel)
                                
                        # Handle channel messages
                        elif parsed_msg['command'] == 'PRIVMSG':
                            if parsed_msg['target'].startswith('#'):
                                self.handle_command(parsed_msg)
                                
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