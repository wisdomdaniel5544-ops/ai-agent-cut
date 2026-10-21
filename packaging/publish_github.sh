#!/usr/bin/env bash
# Run AFTER `gh auth login`. Creates public repo ai-agent-cut, pushes code, publishes Release v2.0.0 with the
# installer + APK, and enables GitHub Pages from /docs. Secrets/ and large media are excluded by .gitignore.
set -euo pipefail
cd "$(dirname "$0")/.."
gh auth status
OWNER=$(gh api user -q .login)
[ -d .git ] || git init -b main
git add -A && git commit -qm "AI AGENT CUT v2.0.0" || true
gh repo view "$OWNER/ai-agent-cut" >/dev/null 2>&1 || gh repo create ai-agent-cut --public --source . --remote origin --description "Long video in. Viral clips out. Free AI clip maker."
git push -u origin main
gh release create v2.0.0 dist/AIAgentCut-Setup.exe dist/AIAgentCut.apk dist/SHA256SUMS.txt LICENSE-NOTICES.txt \
  --title "AI AGENT CUT 2.0" --notes-file packaging/RELEASE_NOTES.md
gh api -X POST "repos/$OWNER/ai-agent-cut/pages" -f "source[branch]=main" -f "source[path]=/docs" >/dev/null 2>&1 || true
echo "Download page: https://$OWNER.github.io/ai-agent-cut/"
echo "Release:       https://github.com/$OWNER/ai-agent-cut/releases/latest"
