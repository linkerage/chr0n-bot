# Replit Setup Guide for chr0n-bot

## Quick Start

1. **Import to Replit**
   - Go to [Replit.com](https://replit.com)
   - Click "Create Repl"
   - Select "Import from GitHub"
   - Paste: `https://github.com/linkerage/chr0n-bot.git`

2. **Configure Bot**
   - Copy `config_replit.json` to `config.json`
   - Edit `config.json` with your settings:
     - IRC server details
     - Bot nickname
     - Channels to join
     - NickServ password (if needed)

3. **Set Secrets (Optional)**
   - Click the "Secrets" tab (lock icon) in Replit
   - Add secrets like:
     - `NICKSERV_PASSWORD` - Your NickServ password
     - Any other sensitive credentials

4. **Run the Bot**
   - Click the "Run" button
   - The bot will start and connect to IRC
   - Web server runs on port 8080 for keep-alive

## Keep-Alive Service

The bot includes a built-in web server that responds to HTTP pings. This keeps your Repl alive 24/7.

### Endpoints:
- `GET /` - Bot status (JSON)
- `GET /ping` - Simple ping/pong
- `GET /health` - Health check

### UptimeRobot Setup (Free 24/7 Keep-Alive)

1. Sign up at [UptimeRobot.com](https://uptimerobot.com) (free)
2. Add New Monitor:
   - Monitor Type: HTTP(s)
   - Friendly Name: chr0n-bot
   - URL: `https://your-repl-name.username.repl.co/ping`
   - Monitoring Interval: 5 minutes
3. Save - Your bot will stay alive 24/7!

### Alternative Keep-Alive Services:
- **Koyeb** - Free tier with always-on
- **Render** - Free tier (sleeps after 15 min inactivity)
- **Railway** - Free tier with $5 credit/month
- **Fly.io** - Free tier for small apps

## Environment Variables

You can use environment variables in Replit Secrets:

```python
import os

# In config.json or code:
nickserv_password = os.environ.get('NICKSERV_PASSWORD', '')
```

## File Structure

```
chr0n-bot/
├── main.py              # Entry point (runs bot + web server)
├── ircbot.py            # Main IRC bot code
├── web_server.py        # Keep-alive web server
├── config.json          # Your configuration (create from template)
├── config_replit.json   # Configuration template
├── requirements.txt     # Python dependencies
├── .replit             # Replit configuration
└── REPLIT_SETUP.md     # This file
```

## Troubleshooting

### Bot won't connect to IRC
- Check `config.json` has correct server/port
- Verify Replit can reach external IRC servers
- Check bot logs in console

### Web server not responding
- Verify port 8080 is exposed
- Check for firewall/network issues
- View Replit webview panel

### Bot keeps stopping
- Set up UptimeRobot ping (see above)
- Consider upgrading to Replit Hacker plan for always-on

## Commands

Test your bot with these commands in IRC:

- `!?` - Show all available commands
- `!bud-zone <location>` - Set your timezone
- `!pi` - Collect pi digits at 3:14 AM/PM
- `!strain <name>` - Cannabis strain info
- `!blaze` - Toke with philosophy
- `!craps` - Play dice game
- `!midi` - Music composition

## Support

For issues or questions:
- GitHub: https://github.com/linkerage/chr0n-bot
- IRC: Join the channels listed in your config
