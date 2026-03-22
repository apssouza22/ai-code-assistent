## Project Knowledge


## Core Principles

These principles reduce common LLM coding mistakes. Apply them to every task.

### 1. Think Before Coding

**Don't assume. Don't hide confusion. Surface tradeoffs.**

- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity First

**Minimum code that solves the problem. Nothing speculative.**

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

**The test:** Would a senior engineer say this is overcomplicated? If yes, simplify.

### 3. Surgical Changes

**Touch only what you must. Clean up only your own mess.**

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

**The test:** Every changed line should trace directly to the user's request.

### Tech Stack
- Python 3.12
- 
### Line Length Limits
- 120 characters max


## Package Architecture

### Domain-Based Organization (Required)

Organize code by **business domain**, not by technical layer. Each domain package contains all related components (controllers, services, repositories, entities) together for high cohesion.

**✅ CORRECT - Domain-based organization (Package by Feature):**
- Group all classes by business domain (e.g., `partner/`, `organization/`)
- Each domain package contains: Entity, Repository, Service, Controller, DTOs, Mappers, and domain-specific exceptions
- Use `common/` package ONLY for cross-cutting concerns (exception handlers, security config, shared utilities)


### Shared Package Guidelines

The `common/` package is ONLY for truly cross-cutting concerns:


## Security Guidelines
- Never hardcode secrets in configuration files. All sensitive values must be injected via environment variables or a secrets manager.
- Never expose internal exception messages, stack traces, or system details to API consumers.** This prevents information disclosure that attackers could exploit.
- Always validate and sanitize user input at system boundaries.
- Always use parameterized queries. Never concatenate user input into SQL.
- Never log sensitive data. This includes passwords, tokens, credit card numbers, personally identifiable information (PII), etc.


## Boundaries

### ✅ Always
- Avoid comments describing functionality ensure self describing code
- Organize code by domain package, not by technical layer


### ⚠️ Ask First
- Database schema changes or migrations
- Modifying CI/CD configuration
- Changes to authentication or security configurations
- API endpoint changes that affect external consumers
- Adding new environment variables for secrets

### 🚫 Never
- Create layer-based packages (`controller/`, `service/`, `repository/`, `entity/`)
- Commit secrets, API keys, or credentials


# Task execution plan
Important: Always plan the task step by step before writing code. Ask for permission to proceed with the plan.
Important: Before proceed with the plan, create a new file named `.agent/plans/name-of-the-task.md`. Based on the approved plan, list all necessary implementation steps as GitHub-style checkboxes (`- [ ] Step Description`). Use sub-bullets for granular details within each main step.

- Plans should be detailed enough to execute without ambiguity
- Each task in the plan must include at least one validation test to verify it works
- Assess complexity and single-pass feasibility - can an agent realistically complete this in one go?
- Include a complexity indicator at the top of each plan:
✅ Simple - Single-pass executable, low risk
⚠️ Medium - May need iteration, some complexity
🔴 Complex - Break into sub-plans before executing

**CRITICAL: After you successfully complete each step, you MUST update the `.agent/plans/name-of-the-task.md` file by changing the corresponding checkbox from `- [ ]` to `- [x]`.**
Only proceed to the *next* unchecked item after confirming the previous one is checked off in the file. Announce which step you are starting.

