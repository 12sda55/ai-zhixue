Create a 10-second educational animation video showing a step-by-step procedure for "{{kpName}}" ({{kpId}}).

{{snippet:video-spec}}

{{snippet:pedagogy}}

## Procedure Details
{{kpDescription}}

{{#if hasDependencies}}
## Prerequisites
{{dependencies}}
{{/if}}

## Style Direction
{{styleHint}}

## CRITICAL RULES
- DO NOT display any Chinese text in the video - AI video generators produce garbled text
- DO NOT use step numbers, text labels, or text overlays
- Use ONLY visual elements: colored shapes, progress indicators, animations
- The only text allowed is a brief English title card at the very start (1 second)

## Video Structure (10 seconds)
1. **Title Card** (0-1s): Brief English title "{{kpId}}" on clean background
2. **Initial State** (1-2s): Show the starting configuration with colored shapes
3. **Step-by-Step Process** (2-8s): Animate each step using ONLY:
   - Current element highlighted in orange
   - Completed elements in green
   - Remaining elements in blue/gray
   - Arrows showing the direction of progress
   - NO text, NO numbers, NO labels
4. **Final Result** (8-10s): All elements turn green (complete), clean fade out

## Animation Requirements
- Progress shown through color transitions (blue→orange→green)
- Current step has a subtle glow or pulse animation
- Smooth transitions between steps
- Visual progress bar at the bottom (colored fill, NO text)

{{#if generateAudio}}
{{snippet:audio-spec}}
{{/if}}
