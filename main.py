#!/usr/bin/env python3
"""
Main entry point for chr0n-bot on Replit
"""
import sys
import traceback

try:
    from ircbot import IRCBot
    from web_server import WebServer
    import os
    
    if __name__ == "__main__":
        print("Starting chr0n-bot...")
        
        # Start web server for Replit keep-alive
        port = int(os.environ.get('PORT', 8080))
        print(f"Starting web server on port {port}...")
        web_server = WebServer(port=port)
        web_server.start()
        
        # Start IRC bot
        print("Initializing IRC bot...")
        bot = IRCBot("config.json")
        
        print("Connecting to IRC server...")
        if bot.connect():
            print("Connected! Bot is now running.")
            print("Web server available for keep-alive pings.")
            bot.listen()  # Use listen() instead of run() to avoid double disconnect
        else:
            print("ERROR: Failed to connect to IRC server")
            sys.exit(1)
            
except Exception as e:
    print(f"\n=== FATAL ERROR ===")
    print(f"Error: {e}")
    print(f"\nFull traceback:")
    traceback.print_exc()
    print(f"\n=== Please report this error ===")
    sys.exit(1)
