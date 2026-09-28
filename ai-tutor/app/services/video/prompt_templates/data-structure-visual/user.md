Create a 10-second educational animation video visualizing the data structure "{{kpName}}" ({{kpId}}).

{{snippet:video-spec}}

{{snippet:pedagogy}}

## Data Structure Details
{{kpDescription}}

{{#if hasDependencies}}
## Related Structures
Built upon: {{dependencies}}
{{/if}}

## Style Direction
{{styleHint}}

## CRITICAL RULES
- DO NOT display any Chinese text in the video - AI video generators produce garbled text
- DO NOT use text labels inside nodes or on arrows
- Use ONLY visual elements: colored shapes, connecting lines, animations
- The only text allowed is a brief English title card at the very start (1 second)

## Video Structure (10 seconds)
1. **Title Card** (0-1s): Brief English title "{{kpId}}" on clean background
2. **Structure Build** (1-4s): Animate the data structure appearing piece by piece:
   - Nodes as colored circles or rounded rectangles (NO text inside)
   - Edges/pointers as animated arrows connecting nodes
   - Build from empty to complete structure
3. **Core Operation** (4-8s): Animate the primary operation:
   - A new node appears (orange highlight)
   - Arrows show traversal path
   - Node moves to its position
   - Connected edges animate into place
   - Completed nodes turn green
4. **Final State** (8-10s): Complete structure shown, clean fade out

## Animation Requirements
- Nodes: colored circles (empty, no text inside)
- Arrows: animated lines with directional flow
- New element: orange glow, then transitions to green when placed
- Traversal path: highlighted with bright color trail
- Smooth easing animations throughout

{{#if generateAudio}}
{{snippet:audio-spec}}
{{/if}}
