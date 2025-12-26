#!/bin/bash
set -e

echo "🚀 Pharmyrus v27 - Railway Deployment Script"
echo "=============================================="
echo

# Check if git is initialized
if [ ! -d .git ]; then
    echo "📦 Initializing git repository..."
    git init
    git branch -M main
fi

# Add all files
echo "📝 Adding files..."
git add .

# Commit
echo "💾 Committing changes..."
git commit -m "Pharmyrus v27: EPO + Google Patents integration" || echo "No changes to commit"

# Check if remote exists
if ! git remote | grep -q origin; then
    echo
    echo "⚠️  No remote repository configured!"
    echo
    echo "To deploy to Railway:"
    echo "1. Create a new GitHub repository"
    echo "2. Run: git remote add origin <your-repo-url>"
    echo "3. Run: git push -u origin main"
    echo "4. Connect the repo to Railway"
    echo
else
    echo "🚀 Pushing to GitHub..."
    git push -u origin main
    echo
    echo "✅ Pushed to GitHub!"
    echo "Now connect this repository to Railway to deploy."
fi

echo
echo "=============================================="
echo "✅ Deployment preparation complete!"
