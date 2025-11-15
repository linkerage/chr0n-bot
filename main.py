#!/usr/bin/env python3
"""
Main entry point for chr0n-bot on Replit
"""
from ircbot import IRCBot

if __name__ == "__main__":
    bot = IRCBot("config.json")
    bot.connect()
    bot.run()
