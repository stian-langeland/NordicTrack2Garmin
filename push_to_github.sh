#!/bin/bash
# Helper script to push to GitHub
# First create the repo on GitHub, then run this script with your username

if [ -z "$1" ]; then
    echo "Usage: ./push_to_github.sh YOUR_GITHUB_USERNAME"
    echo ""
    echo "First, create a new repository on GitHub:"
    echo "  1. Go to https://github.com/new"
    echo "  2. Repository name: NordicTrack2Garmin"
    echo "  3. Don't initialize with README"
    echo "  4. Click 'Create repository'"
    echo ""
    echo "Then run: ./push_to_github.sh your_username"
    exit 1
fi

GITHUB_USERNAME=$1
REPO_NAME="NordicTrack2Garmin"

echo "Setting up remote for GitHub repository..."
echo "Repository: https://github.com/$GITHUB_USERNAME/$REPO_NAME"
echo ""

# Add remote
git remote add origin "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"

# Rename branch to main
git branch -M main

# Push to GitHub
echo "Pushing to GitHub..."
git push -u origin main

echo ""
echo "✅ Done! Your repository is now on GitHub:"
echo "   https://github.com/$GITHUB_USERNAME/$REPO_NAME"
