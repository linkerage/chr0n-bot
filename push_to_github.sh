#!/bin/bash

echo "🚀 Chr0n-Bot GitHub Push Helper"
echo "=================================="
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Error: Not in a git repository!"
    exit 1
fi

echo "📋 Before we start, make sure you have:"
echo "   1. Created the repository 'chr0n-bot' on GitHub"
echo "   2. Generated a Personal Access Token with 'repo' permissions"
echo ""
echo "🔗 Links:"
echo "   • Create repo: https://github.com/new"
echo "   • Get token: https://github.com/settings/tokens/new"
echo ""

read -p "✅ Have you done both steps above? (y/N): " ready
if [[ ! $ready =~ ^[Yy]$ ]]; then
    echo ""
    echo "📝 Instructions:"
    echo "1. Go to https://github.com/new"
    echo "   - Repository name: chr0n-bot"
    echo "   - Make it Public"
    echo "   - Don't initialize with README"
    echo "   - Click 'Create repository'"
    echo ""
    echo "2. Go to https://github.com/settings/tokens/new"
    echo "   - Note: 'Chr0n-bot access'"
    echo "   - Expiration: 90 days (or your choice)"
    echo "   - Scopes: Check 'repo'"
    echo "   - Click 'Generate token'"
    echo "   - Copy the token (starts with ghp_)"
    echo ""
    echo "Run this script again when ready!"
    exit 0
fi

echo ""
read -p "🔑 Enter your GitHub username [linkerage]: " username
username=${username:-linkerage}

echo ""
echo "🔐 Enter your Personal Access Token:"
echo "    (This will be hidden as you type)"
read -s token

if [ -z "$token" ]; then
    echo ""
    echo "❌ Error: No token provided!"
    exit 1
fi

echo ""
echo "🔄 Setting up remote and pushing to GitHub..."

# Set up the remote URL with credentials
git remote set-url origin "https://${username}:${token}@github.com/${username}/chr0n-bot.git"

# Push to GitHub
echo "📤 Pushing to GitHub..."
if git push -u origin main; then
    echo ""
    echo "🎉 SUCCESS! Your chr0n-bot is now on GitHub!"
    echo "🌐 View it at: https://github.com/${username}/chr0n-bot"
    echo ""
    
    # Clean up the credentials from the remote URL for security
    git remote set-url origin "https://github.com/${username}/chr0n-bot.git"
    echo "🔒 Cleaned up credentials from git config for security."
    echo ""
    echo "💡 Your IRC friends can now get the code from:"
    echo "   https://github.com/${username}/chr0n-bot"
    echo ""
    echo "🔔💨 Blaze on!"
    
else
    echo ""
    echo "❌ Push failed! Common issues:"
    echo "   • Repository doesn't exist on GitHub"
    echo "   • Wrong username or token"
    echo "   • Token doesn't have 'repo' permissions"
    echo ""
    echo "Double-check your setup and try again!"
    
    # Clean up credentials anyway
    git remote set-url origin "https://github.com/${username}/chr0n-bot.git"
fi