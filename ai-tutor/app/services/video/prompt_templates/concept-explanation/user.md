Create a 10-second educational animation video about "{{kpName}}" ({{kpId}}) in computer science.

{{snippet:video-spec}}

{{snippet:pedagogy}}

## Concept Details
{{kpDescription}}

{{#if hasDependencies}}
## Prerequisites
This concept builds on: {{dependencies}}
{{/if}}

## Style Direction
{{styleHint}}

## CRITICAL RULES
- DO NOT display any Chinese text in the video - AI video generators produce garbled text
- DO NOT use text overlays or labels inside the animation
- Use ONLY visual elements: shapes, colors, arrows, animations to convey meaning
- The only text allowed is a brief English title card at the very start (1 second)

## Video Structure (10 seconds)
1. **Title Card** (0-1s): Brief English title "{{kpId}}" on clean background, then fade out
2. **Visual Concept** (1-7s): Animate the core idea using ONLY:
   - Colored shapes (circles, rectangles, arrows)
   - Smooth animations (movement, scaling, color changes)
   - Color coding: green=complete, orange=active, red=error
3. **Key Visual** (7-9s): Highlight the most important visual pattern with a zoom or glow effect
4. **Closing** (9-10s): Clean fade out

## Animation Style
- Modern, clean, minimal design
- Smooth easing animations
- Focus on visual storytelling, NOT text explanation
- Use motion and color to guide the viewer's attention

{{#if generateAudio}}
{{snippet:audio-spec}}
{{/if}}
