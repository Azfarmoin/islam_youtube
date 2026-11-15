# Script writing and Director: 100 improvements

Generated from `ivs/features.py`. **75 built**, **25 planned** (not built, no switch). Switches live on the dashboard page *Script & Director*.

Honest limits: these are rule-based checks and choices. They do not judge religious accuracy (the verification gate and a human do), and nothing here guarantees views. Anything the lint flags is sent to human review.

## Hooks and openings

| Item | Status | Switch | What it does |
|---|---|---|---|
| Several hook candidates per video | done |  | Standard, authored and variant lines compete; the best is chosen. |
| Transparent hook scoring | done |  | Curiosity, emotion, relevance, clarity, naturalness and retention, each visible. |
| Hook variants | done | script.hook_variants | More non-clickbait opening lines per category, through the same filters. |
| Short hooks | done | script.hook_brevity | Prefers hooks readable in about 3 seconds (9 words). |
| Clickbait and false-promise filter | done |  | Rejects 'shocking', 'secret', guarantees and reward promises. |
| No repeated openings | done |  | Rejects a hook whose pattern or wording was used recently. |
| Author-written hooks win ties | done |  | A line a person wrote beats template filler. |
| Hook appears word by word | done |  | The opening line is revealed with the voice. |
| Opening shot never repeats | done |  | The Director avoids last video's first shot. |
| Hooks matched to detected feeling | planned |  | Pick the hook by the passage's emotion beyond a few keywords. |

## Voice and narration writing

| Item | Status | Switch | What it does |
|---|---|---|---|
| Spoken-style text for the narrator | done | script.spoken_style | Chapter/verse numbers, honorifics and symbols are spoken naturally (screen text is untouched). |
| Humanised pauses and pace | done |  | Sentence-by-sentence delivery (switch on the Settings page). |
| Narration on every video | done |  | Hook, context, translation and takeaway are spoken (switch on the Look & Story page). |
| Plain-language check | done |  | Flags editorial lines above about grade 9 (part of the lint switch). |
| Urdu narration | done |  | Urdu lines are spoken with a free local voice (quality is basic). |
| Sentence rhythm variation | planned |  | Mix short and long sentences on purpose. |
| Arabic name pronunciation hints | planned |  | Respell names so the voice says them well (needs listening tests). |
| Tone profiles | planned |  | Calm, warm or urgent delivery per theme. |
| Breath and pause markup | planned |  | Author-marked pauses in story lines. |
| Keyword emphasis | planned |  | Stress the one word that carries the line. |

## Structure and arc

| Item | Status | Switch | What it does |
|---|---|---|---|
| Context before, takeaway after | done | script.enabled | Labelled editorial lines around the verse. |
| Emotional beat map | done | script.beat_map | Planned intensity per scene: curiosity, rise, turning point, release. |
| Arc check | done |  | Warns when nothing rises above the opening or the ending does not release (part of the beat-map switch). |
| Fixed skeleton | done |  | Hook, context, verse, translation, takeaway, outro in every video. |
| Part numbers and next-part line | done | script.series_teaser | 'Part 1 of 3: part 2 is next.' on split stories, outro and description. |
| Long stories split into parts | done |  | Cut at line boundaries, never edited. |
| Chapters | done |  | Timestamped chapters in story descriptions. |
| Callback ending | planned |  | The last line echoes the hook. |
| Chosen cliffhanger points | planned |  | Pick split points that leave a question open. |
| Three-act template for AI drafts | planned |  | Drafts follow setup, turn, resolution. |

## Titles and descriptions

| Item | Status | Switch | What it does |
|---|---|---|---|
| Several title candidates | done |  | Five per video, built from the theme and reference. |
| Title scoring | done | script.title_scoring | Best length, keyword and reference win; shouting and false promises lose. |
| Choose the title on the dashboard | done |  | Pick any scored candidate on the video page. |
| Viral, classic or minimal descriptions | done |  | Choose on the Settings page. |
| Reflective comment question | done |  | One honest question in the outro and description (switch on the Look & Story page). |
| Relevant hashtags | done |  | Up to 15, only true ones (reciter only when used). |
| Chapters and evidence lines in the description | done |  | Sources and verification are listed. |
| Pinned comment with sources | planned |  | Post the sources as the first comment. |
| A/B title rotation | planned |  | Swap titles after a few days; keep the winner. |
| Urdu title and description | planned |  | A second-language title. |

## Accuracy and safety in the script

| Item | Status | Switch | What it does |
|---|---|---|---|
| Editorial lint | done | script.editorial_lint | Flags promises, rulings, invented quotes, judging others, shouting, over-long or hard lines; a person must review them. |
| No invented quotations | done |  | Quotation marks in editorial lines are flagged (part of the lint switch). |
| No reward or outcome promises | done |  | 'Guaranteed', 'you will be forgiven' and similar are flagged (part of the lint switch). |
| No rulings in editorial lines | done |  | 'You must', 'is haram' and similar are flagged (part of the lint switch). |
| Verse text verified | done |  | Exact text checked against pinned editions. |
| Claims table | done |  | Every claim stored with source, translator, grade and review status. |
| A/B/C/D claim classes | done |  | Established, interpretation, reconstruction, metaphor. |
| Human review of stories, hadith and AI drafts | done |  | Never skipped. |
| Forbidden-depiction guard | done |  | Storyboards that mention prophets, angels, faces or Allah fail. |
| Source-support check for AI drafts | done |  | Each drafted line must be supported by the cited text. |

## Director: shot design

| Item | Status | Switch | What it does |
|---|---|---|---|
| Twelve camera moves | done |  | Each with a purpose (reveal, journey, scale). |
| Camera variety lint | done |  | No identical moves back to back; at least three kinds. |
| Composition rules | done |  | Thirds, low or high horizon, symmetry per treatment. |
| A purpose for every scene | done |  | Scenes without a storytelling purpose fail the check. |
| Faceless cast only | done |  | Only generic silhouettes can be staged. |
| 3D budget by distinct looks | done |  | 3D seconds go to different-looking moments. |
| Camera family per treatment | done |  | A treatment limits the camera to a coherent family. |
| Ground-level shots only with ground actors | done |  | No macro-feet shot of an empty sky. |
| Shot list preview on the dashboard | planned |  | See the planned shots before rendering. |
| Storyboard thumbnails | planned |  | A contact sheet of planned frames. |

## Director: pacing and rhythm

| Item | Status | Switch | What it does |
|---|---|---|---|
| Pace profiles | done |  | Each treatment has a pace and minimum hold. |
| Minimum hold per scene | done |  | No scene is cut shorter than readable. |
| Narration-free scenes | done |  | Some scenes are left to ambience on purpose. |
| Fast pace mode | done |  | Tighter holds (switch on the Settings page). |
| Hard 59-second cap | done |  | Lean retry if a render runs long. |
| Beat map drives the pace | planned |  | Hold longer at the turning point, shorter in the build. |
| Variable pace by section | planned |  | Slow on the verse, quick on context. |
| Pattern interrupt around 20 seconds | planned |  | A deliberate change to win back attention. |
| A breath before the takeaway | planned |  | A beat of stillness before the lesson. |
| Loop-friendly ending | planned |  | The last frame flows into the first. |

## Look and sound direction

| Item | Status | Switch | What it does |
|---|---|---|---|
| Style library | done |  | Grade, typography, transition and animation per treatment. |
| Typography personality | done |  | Editorial, classical, luxury, calligraphic or educational. |
| Transition family and colour | done |  | Consistent cuts within a video. |
| Lighting overrides for 3D | done |  | Sun and sky follow the treatment. |
| Sound plan with no music | done |  | Ambience and effects only; recitation first. |
| Ambience lowers in silent scenes | done |  | Quiet means quiet. |
| One palette per story | done |  | Consistent clothing and colour inside a story. |
| Metaphor engine | done |  | Words map to light, water, pattern, labelled as metaphor. |
| Look preset per treatment | planned |  | A treatment picks its finishing look automatically. |
| Sound motifs per theme | planned |  | A recurring quiet sound for each theme. |

## Continuity and variety

| Item | Status | Switch | What it does |
|---|---|---|---|
| Direction log | done |  | Recent cameras, transitions and styles are avoided. |
| Character design stays fixed | done |  | Same palette across re-renders. |
| Style rotation | done |  | Treatments rotate across videos. |
| Topic variety window | done |  | Recent topics are not repeated. |
| Hook, title and CTA rotation | done |  | No repeated wording. |
| Production bible | done |  | Atmosphere, materials and rules per video. |
| Continuity checklist | done |  | Items needing a person are marked MANUAL, never ticked for you. |
| Re-render keeps the design | done |  | Same storyboard and palette. |
| Visual identity per series | planned |  | Parts of one story share a look. |
| Seasonal direction | planned |  | Ramadan and Jumu'ah mood. |

## Review and learning loop

| Item | Status | Switch | What it does |
|---|---|---|---|
| Director's package | done |  | Markdown and JSON next to every story video. |
| Film plan and frame records | done |  | Scene blocks, production table and prompts. |
| Pre-publication score | done |  | A transparent heuristic, never a substitute for accuracy. |
| Script lab on the dashboard | done |  | Preview hooks, titles, lint and the spoken version without rendering. |
| Hook insights | done |  | Which hook shapes earn views, once stats exist. |
| Review queue and approve | done |  | Everything that needs a person waits there. |
| Edit title, description and tags | done |  | Before anything goes out. |
| Audit trail of candidates | done |  | All scored hooks and titles are stored. |
| Learn from analytics | planned |  | Re-weight scoring from real results. |
| Retention-curve feedback | planned |  | Needs the YouTube Analytics API. |
