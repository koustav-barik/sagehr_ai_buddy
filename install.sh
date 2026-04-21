#!/usr/bin/env bash
# install.sh — Links sagehr_ai_buddy artefacts into a target Rails repo
#
# Usage:
#   ./install.sh                        # installs into ../rails-cakehr (default)
#   ./install.sh /path/to/rails-cakehr  # installs into a custom path
#
# What it does:
#   Creates symlinks inside the target repo's .github/ directory pointing back
#   to this repo's agents/, prompts/, instructions/, learnings/, and playbooks/
#   directories. Because they are symlinks, any git pull here is immediately
#   reflected there.
#
#   NOTE: skills/ is intentionally NOT symlinked. It is reserved for future
#   official Copilot skills that may be promoted to rails-cakehr directly.
#
#   NOTE: playbooks/ contains SageHR-internal procedures and must be excluded
#   from git tracking in rails-cakehr. The installer prints instructions for
#   this after linking.
#
# To uninstall:
#   cd <target-repo>/.github && rm agents prompts instructions learnings playbooks
#   cd <target-repo> && rm scripts

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-"$(cd "$SCRIPT_DIR/.." && pwd)/rails-cakehr"}"

if [ ! -d "$TARGET" ]; then
  echo "Error: Target directory does not exist: $TARGET"
  echo "Usage: ./install.sh [/path/to/target-repo]"
  exit 1
fi

echo "📦 sagehr_ai_buddy installer"
echo "   Source: $SCRIPT_DIR"
echo "   Target: $TARGET"
echo ""

# Ensure .github exists in the target
mkdir -p "$TARGET/.github"

LINKED=0
SKIPPED=0

# Link .github subdirectories (agents, prompts, instructions, learnings, playbooks)
# NOTE: skills/ is intentionally excluded — reserved for future official Copilot skills
for dir in agents prompts instructions learnings playbooks; do
  SOURCE_PATH="$SCRIPT_DIR/.github/$dir"
  TARGET_PATH="$TARGET/.github/$dir"

  if [ -L "$TARGET_PATH" ]; then
    echo "  ⏭  .github/$dir already symlinked, skipping"
    ((SKIPPED++))
  elif [ -d "$TARGET_PATH" ]; then
    echo "  ⚠️  .github/$dir exists as a real directory in $TARGET"
    echo "     To link, manually remove or rename it first:"
    echo "     mv $TARGET_PATH $TARGET_PATH.backup"
    ((SKIPPED++))
  else
    ln -s "$SOURCE_PATH" "$TARGET_PATH"
    echo "  ✅ Linked .github/$dir → $TARGET_PATH"
    ((LINKED++))
  fi
done

# Link scripts/ at the repo root (needed for ./scripts/jira-fetch.sh in agents)
SCRIPTS_SOURCE="$SCRIPT_DIR/scripts"
SCRIPTS_TARGET="$TARGET/scripts"

if [ -L "$SCRIPTS_TARGET" ]; then
  echo "  ⏭  scripts/ already symlinked, skipping"
  ((SKIPPED++))
elif [ -d "$SCRIPTS_TARGET" ]; then
  echo "  ⚠️  scripts/ exists as a real directory in $TARGET"
  echo "     To link, manually remove or rename it first:"
  echo "     mv $SCRIPTS_TARGET $SCRIPTS_TARGET.backup"
  ((SKIPPED++))
else
  ln -s "$SCRIPTS_SOURCE" "$SCRIPTS_TARGET"
  echo "  ✅ Linked scripts/ → $SCRIPTS_TARGET"
  ((LINKED++))
fi

echo ""
echo "Done. $LINKED linked, $SKIPPED skipped."
echo ""
echo "Reload VS Code in $TARGET to see the new agents and prompts:"
echo "  - Type / in Copilot Chat to browse prompts"
echo "  - Select an agent from the mode picker (Ask/Agent/Plan dropdown)"
echo ""
echo "-----------------------------------------------------------------------"
echo " IMPORTANT: Exclude symlinks from git tracking in $TARGET"
echo "-----------------------------------------------------------------------"
echo ""
echo " The symlinked directories and .env.jira must not be committed by"
echo " the rails-cakehr repo. Run this once to add them to the local-only"
echo " git exclude file (never committed, never shared):"
echo ""
echo "   cat >> $TARGET/.git/info/exclude << 'EOF'"
echo ""
echo "   # sagehr_ai_buddy symlinks and Jira credentials (local only)"
echo "   .github/agents"
echo "   .github/instructions"
echo "   .github/prompts"
echo "   .github/learnings"
echo "   .github/playbooks"
echo "   .env.jira"
echo "   scripts"
echo "   EOF"
echo ""
echo " NOTE: .github/skills is intentionally not excluded — it is reserved"
echo " for future official skills and will be added deliberately when ready."
echo "-----------------------------------------------------------------------"
