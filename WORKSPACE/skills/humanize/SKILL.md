---
name: humanize-text
description: >
 Use this skill whenever the user needs to make AI-generated text sound more human, "less robotic," or needs to bypass AI detection. Trigger this for any request involving "humanizing" text, writing "natural" emails, stripping "AI-polish," or creating content that avoids the typical markers of LLM writing. Even if the user doesn't explicitly say "humanize," if they ask for "casual," "raw," or "non-academic" versions of AI text, use this skill.
---

# Humanize Text Skill (Sinceerly-Inspired)

This skill transforms polished AI output into natural, human-like text by simulating linguistic imperfections and shifting lexical patterns.

## Core Objective
Strip the "AI-polish" from text to bypass AI detection and psychological filters that identify "too-perfect" writing.

## Implementation Logic
You must use the `skills/user/humanize/scripts/humanize_engine.py` script to process the text. Do not attempt to "manually" humanize text using general prompting alone; the engine provides the necessary stochastic noise and lexical mapping.

### Processing Pipeline:
1. **Lexical Shift**: Replaces high-probability AI markers (e.g., "Furthermore," "In conclusion," "Moreover") with human equivalents.
2. **Contraction Mapping**: Converts formal phrasing into casual syntax.
3. **Morphological Noise**: Injects stochastic typos (swaps, doubles, drops) based on the chosen profile.

## Profile Selection
Select the profile based on the user's desired "vibe":

- **casual**: Standard human-like text. Low noise (5%). Best for general emails, blogs, and messages.
- **distracted**: Simulates haste or lack of focus. Higher noise (12%). Best for quick chats, texts, or "rough draft" feel.
- **non-native**: Simulates ESL (English as a Second Language) patterns. Moderate noise (8%). Best for simulating non-native speakers.

## Operational Workflow
1. **Identify Input**: Capture the AI-generated text to be humanized.
2. **Choose Profile**: Match the user's intent to one of the three profiles (casual, distracted, non-native).
3. **Execute Engine**: Run the `skills/user/humanize/scripts/humanize_engine.py` script via bash.
4. **Review and Deliver**: Present the output to the user.

## Output Format
Provide the result as follows:
- **Original**: [Brief snippet or reference to original]
- **Profile Used**: [Profile Name]
- **Humanized Text**: 
[The processed text here]

## Example Trigger
User: "This email sounds too much like a bot, make it look like I wrote it while I was in a rush."
Action: Trigger `humanize-text` -> Select `distracted` profile -> Run `humanize_engine.py`.
