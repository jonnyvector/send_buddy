# UI/UX Review Workflow

This document describes how to use the UI/UX reviewer and frontend developer agents together.

## Prerequisites

1. **Playwright MCP Server** must be installed:
   ```bash
   claude mcp add playwright npx @executeautomation/playwright-mcp-server
   ```

2. **Load agents** (if you just created them):
   ```bash
   /agents
   ```

3. **Verify MCP server** is working:
   ```bash
   /mcp
   ```

## Agent Locations

- **UI/UX Reviewer**: `.claude/agents/ui-ux-reviewer.md`
- **Frontend Developer**: `backend/.claude/agents/nextjs-frontend-dev.md`

## Workflow

### Step 1: Run UI/UX Review

```bash
/task prompt:"Review the [page name] at http://localhost:[port]/[path]" subagent_type:ui-ux-reviewer
```

**Examples:**
```bash
/task prompt:"Review the login page at http://localhost:3001/auth/login" subagent_type:ui-ux-reviewer

/task prompt:"Review the trip creation form at http://localhost:3001/trips/new" subagent_type:ui-ux-reviewer

/task prompt:"Review the profile page at http://localhost:3001/profile" subagent_type:ui-ux-reviewer
```

**What happens:**
- Agent navigates to the URL using Playwright
- Takes screenshots
- Analyzes UI/UX (visual hierarchy, accessibility, spacing, etc.)
- Writes detailed feedback to `ui-ux-review-[page-name]-[date].md` in project root
- Categorizes issues by priority: Critical 🔴 → Medium 🟡 → Polish 🟢

### Step 2: Implement Feedback

```bash
/task prompt:"Implement the UI/UX improvements from the latest review" subagent_type:nextjs-frontend-dev
```

**What happens:**
- Frontend dev agent looks for `ui-ux-review-*.md` files
- Reads and prioritizes feedback
- Implements changes while maintaining architecture patterns
- Follows Next.js best practices and existing component patterns

### Step 3: Re-review (Optional)

After changes are implemented, run another review to verify improvements:

```bash
/task prompt:"Re-review the [page name] to verify UI/UX improvements" subagent_type:ui-ux-reviewer
```

## Tips

### Review Multiple Pages
You can review multiple pages and the frontend dev will handle all feedback files:

```bash
/task prompt:"Review the entire auth flow (login, register, verify)" subagent_type:ui-ux-reviewer
```

### Specific Focus Areas
Be specific about what you want reviewed:

```bash
/task prompt:"Review the mobile responsiveness of the trips list page" subagent_type:ui-ux-reviewer

/task prompt:"Review accessibility and color contrast on the dashboard" subagent_type:ui-ux-reviewer
```

### Implementing Specific Priorities
Tell the frontend dev to focus on certain priorities:

```bash
/task prompt:"Implement only the critical UI/UX issues from the latest review" subagent_type:nextjs-frontend-dev

/task prompt:"Implement all medium and critical UI/UX improvements" subagent_type:nextjs-frontend-dev
```

## Review File Format

The UI/UX reviewer creates files like: `ui-ux-review-login-2026-01-14.md`

Structure:
- ✅ What Works Well
- 🔴 Critical Issues (High Priority)
- 🟡 Improvements (Medium Priority)
- 🟢 Polish (Low Priority)
- Code-level recommendations

## Troubleshooting

### MCP Server Not Working
1. Restart Claude Code session
2. Run `/mcp` to verify
3. Check `~/.claude.json` has playwright server configured

### Agents Not Showing
1. Run `/agents` to reload
2. Verify files exist in `.claude/agents/`
3. Restart session if needed

### Frontend Dev Not Finding Reviews
- Ensure review files are in project root (not in subdirectories)
- Check file naming: `ui-ux-review-*.md`
- Verify files were actually created by the reviewer

## Advanced: Custom Workflows

You can create an orchestrator agent that runs both automatically, or run them in parallel for multiple pages and batch implement all feedback.
