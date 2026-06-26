# ArtifactX Skills

This file documents skills available for ArtifactX development.

## Installed Skills

| Skill | Purpose | Location |
|-------|---------|----------|
| `find-skills` | Discover and install new skills from the ecosystem | `.agents/skills/find-skills/` |
| `frontend-design` | Distinctive visual design guidance for UI components | `.agents/skills/frontend-design/` |
| `vercel-react-best-practices` | React/Next.js performance optimization guidelines | `.agents/skills/vercel-react-best-practices/` |

---

## Finding New Skills

To find additional skills, browse **https://skills.sh/** or use the CLI:

```bash
# Search for skills
npx skills find [query]

# Install a skill globally
npx skills add <owner/repo@skill> -g -y

# Check for updates
npx skills check
```

### Relevant Search Terms

Based on ArtifactX's stack, relevant search queries include:

| Category | Search Terms |
|----------|--------------|
| Backend | python, fastapi, api, backend |
| Testing | testing, pytest, jest, e2e |
| Security | security, audit, review |
| Code Quality | review, lint, refactor, best-practices |
| Documentation | docs, readme, api-docs |

---

## Skill Usage

| Task | Recommended Skill |
|------|-------------------|
| Adding/changing frontend components | `frontend-design` + `vercel-react-best-practices` |
| Finding new capabilities | `find-skills` |

Currently, ArtifactX does not have skills installed for:
- Backend Python/FastAPI development
- Security auditing
- Testing