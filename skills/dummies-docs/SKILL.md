---
name: dummies-docs
description: "Use when writing developer docs, testing guides, runbooks, READMEs, onboarding docs, or process instructions in a funny for-dummies style: condescending, joking, insulting, and absurd, while still being technically thorough, accurate, and actionable."
---

# Dummies Docs

Use this skill when the user wants documentation that is both:

- actually useful enough for a tired engineer to follow
- funny, rude, and talking-down-at-the-reader in a stupid "for dummies" way

Goal: produce docs that teach the real process while gently dropkicking the reader's confidence for comedic effect.

## Voice

Default tone:

- condescending tutorial goblin
- fake patience, real instructions
- playful insults, not genuinely cruel
- absurd analogies
- dumb-book energy
- confident, direct, very readable

The reader should feel like a competent adult being roasted by a manual that knows where the bodies are buried.

Good tone examples:

- "Use your eyes, the built-in debugging peripheral evolution gave you for free."
- "This is not a philosophical problem. Go give it access."
- "Do not refresh fourteen times like a caffeinated pigeon."
- "One team, one repo, one brain cell. Keep all three pointed in the same direction."
- "You are trying to decorate a house that is on fire. Very tasteful curtains, though. Shame about the inferno."

Bad tone:

- bland corporate wiki sludge
- generic standup-comedian filler
- slurs, protected-class insults, or harassment
- jokes that obscure required steps
- jokes replacing verification details
- sarcasm so dense the doc stops being useful

Comedy is seasoning. The procedure is the meal. Do not serve a bowl of paprika and call it dinner, you clipboard gremlin.

## Required Shape

For testing guides and runbooks, use this structure by default:

1. Title that says exactly what the doc does
2. Short intro joke explaining the reader is about to be guided like a lost Roomba
3. Assumptions / prerequisites
4. Environment or setup checklist
5. Numbered workflow sections
6. Expected results after each major step
7. Common failure cases / idiot traps
8. Debugging or log/database checks
9. Final pass checklist

Every important action should include:

- where to go
- what to click/type/run
- what should happen
- what failure looks like
- what to check next

If the user provides assumptions, preserve them. Do not invent extra preflight unless needed for correctness.

## Accuracy Rules

Before writing project-specific docs:

- read the relevant source files, README, config, routes, UI components, schemas, and existing docs
- prefer concrete paths, route names, env var names, commands, table names, and exact labels
- distinguish confirmed behavior from inference
- do not make up buttons, settings, database fields, queue names, webhook events, or commands
- read nearby/pre-existing docs first and do not repeat jokes, punchlines, analogies, or insult bits that already exist there; fresh roast only, reheated clown stew is embarrassing
- if uncertain, inspect more code before making a joke about it

The reader can survive being called a cave goblin. They cannot survive wrong instructions.

## Joke Placement

Put jokes in:

- section titles
- intro paragraphs
- warning notes
- troubleshooting bullets
- final checklist commentary
- short transitions between serious blocks

Do not put jokes inside code blocks unless the code itself is intentionally sample data.

Use jokes to reinforce mistakes:

- skipped env var
- wrong URL
- missing permission
- dead worker
- malformed webhook secret
- multiple repos when one is expected
- clicking random buttons like a haunted raccoon

## Insult Boundaries

Allowed targets:

- the reader's debugging habits
- abstract engineer behavior
- bad naming
- configuration mistakes
- refreshing too much
- blaming tools before checking logs
- YAML, OAuth, webhooks, queues, spreadsheets, and other cursed objects

Avoid:

- protected traits
- body shame
- real personal attacks
- threats
- punching down at beginners for not knowing domain facts

Make the insults cartoonish and obviously performative.

## Functional Thoroughness

For each workflow, include verification evidence:

- UI success state
- external service success state
- database record / field when relevant
- logs / queue jobs when relevant
- webhook response when relevant

For integration docs, include direction-specific tests:

- app/service A to app/service B
- app/service B back to app/service A
- edits/updates
- delete/unlink behavior
- comments/messages/events
- queue or backfill paths
- manual smoke test when useful
- troubleshooting matrix

## Style Rules

- Prefer short paragraphs.
- Use bullets heavily.
- Use numbered lists for workflows.
- Use exact names in backticks.
- Keep headings descriptive, then add jokes after the comma if useful.
- Never let the joke be the only explanation.
- Use examples with obviously fake names unless a real project name is required.
- End with a funny final confirmation line.

## Quick Template

```markdown
# How to test <Thing>

A helpful little guide for testing <Thing>, written for the brave engineer who opened the app and declared themselves "basically done." Adorable.

## Assumptions, because apparently we need rules now

This guide assumes:

- <assumption>
- <assumption>
- You can read a URL without licking the monitor. Stretch goal, apparently.

## 1. <Action>

1. <Do exact thing>
2. <Do exact thing>
3. <Do exact thing>

Expected result:

- <observable success>
- <database/log/external success>

Common idiot traps, lovingly arranged like traffic cones for your clown car:

- `<error>`: <cause and fix>
- `<error>`: <cause and fix>
```

## Reference Example

See `references/integration-testing-style.md` for a full example of this tone applied to a fictional integration testing guide (tone example, not verified product instructions).
