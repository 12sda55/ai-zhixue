Create a 10-second educational animation video comparing "{{kpName}}" with related approaches.

{{snippet:video-spec}}

{{snippet:pedagogy}}

## Comparison Context
{{kpDescription}}

{{#if hasDependencies}}
## Related Concepts
{{dependencies}}
{{/if}}

## Style Direction
{{styleHint}}

## CRITICAL RULES
- DO NOT display any Chinese text in the video - AI video generators produce garbled text
- DO NOT use text labels, comparison tables, or text overlays
- Use ONLY visual elements: colored shapes, split-screen animations, speed differences
- The only text allowed is a brief English title card at the very start (1 second)

## Video Structure (10 seconds)
1. **Title Card** (0-1s): Brief English title "{{kpId}}" on clean background
2. **Split Screen** (1-3s): Two sides appear with different colored themes (left=blue, right=purple)
3. **Side-by-Side Process** (3-8s): Animate both approaches simultaneously:
   - Left side: one approach with blue-themed bars/shapes
   - Right side: another approach with purple-themed bars/shapes
   - Show speed difference through animation pace
   - Faster approach finishes first with a green checkmark
4. **Visual Winner** (8-10s): The faster/smaller approach glows green, clean fade out

## Animation Requirements
- Split screen: vertical divider line
- Each side uses its own color theme
- Speed difference shown through animation timing
- NO text labels or comparison metrics

{{#if generateAudio}}
{{snippet:audio-spec}}
{{/if}}
