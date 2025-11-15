#!/usr/bin/env python3
"""
Main entry point for chr0n-bot on Replit
"""
from ircbot import IRCBot
from web_server import WebServer
import os

if __name__ == "__main__":
    # Start web server for Replit keep-alive
    port = int(os.environ.get('PORT', 8080))
    web_server = WebServer(port=port)
    web_server.start()
    
    # Start IRC bot
    bot = IRCBot("config.json")
    bot.connect()
    bot.run()
