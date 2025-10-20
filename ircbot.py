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
                "nickname": "Chr0n-bot",
                "username": "Chr0n-bot",
                "realname": "Chr0n-bot",
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
                else:
                    # Old format, migrate
                    self.toke_data = data
                    self.tb_enabled = {}
        except (FileNotFoundError, EOFError):
            self.toke_data = {}  # {user: last_toke_timestamp}
            self.tb_enabled = {}  # {user: True/False}
            
    def save_toke_data(self):
        """Save toke break data to file"""
        try:
            with open(self.toke_file, 'wb') as f:
                data = {
                    'timestamps': self.toke_data,
                    'tb_enabled': self.tb_enabled
                }
                pickle.dump(data, f)
        except Exception as e:
            self.logger.error(f"Failed to save toke data: {e}")
        
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
            self.send_message(channel, f"{nick}: Available commands: !help, !ping, !about, !uptime, !gentoo, !time, !churchbong, !toke, !pass, !joint, !dab, !blunt, !bong, !vape, !doombong, !olddoombong, !kylebong, !blaze")
            
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
            
            if nick in self.toke_data:
                # Calculate time since last toke
                last_toke = self.toke_data[nick]
                time_diff = current_time - last_toke
                
                days = int(time_diff // 86400)
                hours = int((time_diff % 86400) // 3600) 
                minutes = int((time_diff % 3600) // 60)
                seconds = int(time_diff % 60)
                
                if days > 0:
                    time_str = f"{days}d {hours}h {minutes}m {seconds}s"
                elif hours > 0:
                    time_str = f"{hours}h {minutes}m {seconds}s"
                elif minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                    
                self.send_message(channel, f"{nick}: Time since last toked: {time_str} 🔔💨")
            else:
                self.send_message(channel, f"{nick}: First churchbong recorded! May the sacred smoke guide you. 🔔💨")
            
            # Update user's last toke time
            self.toke_data[nick] = current_time
            self.save_toke_data()
            
            # If they typed "420", add a random 420 fact
            if args and args[0] == "420":
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
            self.toke_data[nick] = current_time
            self.save_toke_data()
            # No message sent - silent tracking
            
        elif command == "blaze":
            # Special blaze command with message and tracking
            current_time = time.time()
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