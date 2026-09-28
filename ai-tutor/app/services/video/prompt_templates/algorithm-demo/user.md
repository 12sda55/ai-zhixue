Create a 10-second educational animation video demonstrating the algorithm "{{kpName}}" ({{kpId}}) step by step.

{{snippet:video-spec}}

{{snippet:pedagogy}}

## Algorithm Details
{{kpDescription}}

{{#if hasDependencies}}
## Related Concepts
This algorithm relates to: {{dependencies}}
{{/if}}

## Style Direction
{{styleHint}}

## CRITICAL RULES
- DO NOT display any Chinese text in the video - AI video generators produce garbled text
- DO NOT use text overlays, step numbers, or labels inside the animation
- Use ONLY visual elements: colored bars, arrows, highlights, animations
- The only text allowed is a brief English title card at the very start (1 second)

## Video Structure (10 seconds)
1. **Title Card** (0-1s): Brief English title "{{kpId}}" on clean background
2. **Initial State** (1-2s): Show 5-6 colored bars of different heights (representing unsorted data)
3. **Algorithm Steps** (2-8s): Animate the sorting/comparison process using ONLY:
   - Colored bars moving and swapping positions
   - Orange highlight on the currently compared elements
   - Green color for elements in their final position
   - Arrows showing comparison direction
   - NO text labels, NO step numbers, NO code display
4. **Final Result** (8-10s): All bars turn green (sorted), brief celebration animation

## Animation Requirements
- Bars: simple colored rectangles, different heights
- Swaps: smooth horizontal movement animation
- Comparisons: orange glow/highlight on two bars being compared
- Sorted: bars smoothly transition to green
- Keep 5-6 elements maximum for clarity in 10 seconds

{{#if generateAudio}}
{{snippet:audio-spec}}
{{/if}}
