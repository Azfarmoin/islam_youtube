# Look & Story: 100 improvements

Honest status: **59 built** (30 have a switch on the dashboard's Look & Story page or in `config.yaml`), **41 planned** (not built; no switch). "Built" items marked *always on* have no switch.

The finishing pass (`ivs/looks.py`) dresses the picture of every video with FFmpeg only: it never touches the audio or the Quran text. Effects that make files heavy are capped (bitrate limit 6 Mbit/s). Cost: roughly 3 minutes of extra render time per minute of video on a small CPU.

Presets: cinematic, punchy, calm, clean (dashboard > Look & Story).


## Colour and grade

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Mood-matched colour grade | Picks a gentle grade from the theme (warm for hope, cool for warnings, deep night for dua). | built, `look.grade` |
| 2 | Lifted blacks, no crushed shadows | Grades keep detail in the dark; no teal-orange or HDR look. | built, always on |
| 3 | Per-story palette from the Director's treatment | Each story gets its own typography palette and grade. | built, always on |
| 4 | Day, night and dawn skies | Scenery switches between sky palettes to match the moment. | built, always on |
| 5 | Film grain | Fine moving grain so flat gradients feel photographic. | built, `look.grain` |
| 6 | Vignette | Soft dark edges that pull the eye to the centre. | built, `look.vignette` |
| 7 | Sharpen for phone screens | Light sharpening so small text stays crisp after compression. | built, `look.sharpen` |
| 8 | Automatic text-contrast check | Fail a frame when caption contrast is too low. | planned |
| 9 | Caption colours sampled from the scenery | Accent colour of captions follows the picture. | planned |
| 10 | Seasonal palettes (Ramadan, Jumu'ah) | Subtle palette shifts on special days. | planned |

## Light and atmosphere

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Soft bloom glow | Highlights glow gently, like light through haze. | built, `look.bloom` |
| 2 | Candle-light flicker | A slow living brightness variation. | built, `look.flicker` |
| 3 | Drifting gold dust | Particles float across every scene. | built, `video.vfx.particles` |
| 4 | PixiJS sparkle layer | A generated sparkle overlay. | built, `js_fx.pixi` |
| 5 | Animated geometric border | Hyperframes border on verse and hadith videos. | built, `js_fx.frame` |
| 6 | Twinkling stars | Night skies have animated stars. | built, always on |
| 7 | Light rays through clouds | Animated god-rays for hope and guidance scenes. | planned |
| 8 | Moonlight shimmer on water | Reflective shimmer for night sea scenes. | planned |
| 9 | Valley mist | Layered drifting mist for calm scenes. | planned |
| 10 | Warm light leaks | Soft colour leaks at scene changes. | planned |

## Camera and motion

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Slow push-in on the whole video | A gentle zoom that builds intensity over the minute. | built, `look.push_in` |
| 2 | Drift on backgrounds | Slow Ken Burns movement on still backgrounds. | built, `video.vfx.kenburns` |
| 3 | Handheld sway | A tiny organic camera wobble (adds a small zoom to hide edges). | built, `look.handheld` |
| 4 | Punch-in on every cut | A quick zoom accent at each scene change. | built, `look.cut_punch` |
| 5 | Parallax scenery layers | Foreground and background drift at different speeds. | built, always on |
| 6 | Blender 3D key shots | Pre-rendered low-poly 3D shots for key moments. | built, `three_d.enabled` |
| 7 | Whip-pan between scenes | A fast blurred pan as a transition. | planned |
| 8 | Rack focus on the key word | Blur shifts to the picture the word names. | planned |
| 9 | Dolly-zoom on the reveal | A vertigo effect for the turning point of a story. | planned |
| 10 | Orbit camera on 3D landmarks | Slow orbit around a low-poly building or ship. | planned |

## Typography and captions

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Word-by-word hook reveal | The opening line appears word by word. | built, always on |
| 2 | Arabic, Urdu and English stacked | All three languages shown together where it fits. | built, always on |
| 3 | Text fade and ease-up | Captions glide in instead of popping. | built, `video.vfx.text_reveal` |
| 4 | Thin gold progress bar | A slim bar shows how far through the video you are. | built, `look.progress_bar` |
| 5 | Auto font size by line length | Long lines shrink to fit, short ones grow. | built, always on |
| 6 | Always-on text for sound-off viewers | Every spoken line is also on screen. | built, always on |
| 7 | Key-word highlight colour | The word being explained gets an accent colour. | planned |
| 8 | Karaoke highlight synced to the voice | Needs forced alignment of the narration. | planned |
| 9 | Arabic calligraphy write-on | Verse appears as if being written. | planned |
| 10 | Shorts UI safe-zone guide | Preview overlay of where the app covers the picture. | planned |

## Scenery and illustration

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Animated faceless landscapes | Every video gets an animated scene, no stock footage. | built, `video.scenery.enabled` |
| 2 | Props: palms, tents, minarets, boats, pines | Drawn scenery elements that match the story. | built, always on |
| 3 | Scenery matched to the meaning | Scene chosen from the words, not at random. | built, always on |
| 4 | 3 to 6 scenery changes per video | The picture keeps changing through the minute. | built, always on |
| 5 | Word-synced icons | A drawn icon pops up when each picture-word is spoken. | built, `video.word_icons` |
| 6 | Islamic geometric patterns (p5.js) | Generative star lattices for geometric scenes. | built, `js_fx.p5` |
| 7 | Day-to-night arc across a story | Sky gradually changes as the story moves. | planned |
| 8 | Rain, wind and sandstorm layers | Weather that matches the text. | planned |
| 9 | Hand-drawn ink style | An illustrated filter for the whole scene. | planned |
| 10 | 100+ icons (currently 30) | A bigger icon library for more words. | planned |

## Characters and actions

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Faceless silhouettes with meaning-based actions | Walking, looking, carrying, chosen from the sentence. | built, always on |
| 2 | Flocks of birds | A moving band of birds for the relevant verses. | built, always on |
| 3 | Caravan silhouettes | Travelling groups cross the horizon. | built, always on |
| 4 | Hands raised in dua (silhouette) | A faceless silhouette for supplication scenes. | planned |
| 5 | Crowd silhouettes | Communities and nations as moving crowds. | planned |
| 6 | Shadow-puppet storytelling | A shadow-theatre style for old stories. | planned |
| 7 | Animated animals | Camel, elephant, whale as moving silhouettes (icons exist today). | planned |
| 8 | Hands-only close-ups | Writing, giving, holding, without faces. | planned |
| 9 | Object cutaways | Lamp, key, door shots as story beats. | planned |
| 10 | Symbolic light for the unseen | Light and geometry stand in for what is never depicted. | planned |

## Transitions and pacing

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | GL transitions between scenes | Real shader transitions at scene changes. | built, `js_fx.transitions` |
| 2 | Fast pace | Tighter holds and quicker word reveals (choose on the Settings page). | built, always on |
| 3 | Cut flash | A brief brightness accent at each scene change. | built, `look.cut_flash` |
| 4 | Fade in and out | Soft start and end so loops feel clean. | built, `look.edge_fades` |
| 5 | Silent beat before the reveal | The Director can drop sound for a moment. | built, always on |
| 6 | Hard 59-second cap | Every video stays under a minute; render retries leaner. | built, always on |
| 7 | Match cuts on shape | Cut between similar shapes (sun to coin). | planned |
| 8 | Cuts on a quiet pulse | Scene changes land on a soft rhythm. | planned |
| 9 | Variable pace by section | Slow on the verse, quick on context. | planned |
| 10 | Pattern interrupt around 20 seconds | A deliberate change to win back attention. | planned |

## Sound and sync

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Humanised English narration | Kokoro voice, sentence by sentence with natural pauses. | built, `audio.narration.humanize` |
| 2 | Voice on every video | Hook, context, translation and takeaway are spoken. | built, `audio.narration.all_videos` |
| 3 | Effects tied to on-screen action | Sound effects land with what is shown. | built, always on |
| 4 | Ambience bed muted under verses | Quiet atmosphere that never covers the Quran. | built, always on |
| 5 | Authentic recitation, never altered | Real reciter audio at original speed and pitch. | built, `audio.recitation.enabled` |
| 6 | Copyright-free sound mode | Free-licence voice and effects only. | built, `audio.copyright_free` |
| 7 | Ambience ducks under the voice | Automatic volume dip while the narrator speaks. | planned |
| 8 | Room tone and light reverb on narration | Makes the voice sit inside the scene. | planned |
| 9 | Word-accurate voice timing | Icons and highlights land exactly on the word. | planned |
| 10 | Loudness normalised for Shorts | Consistent volume across videos. | planned |

## Story structure and hooks

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Hook in the first 3 seconds | The opening line is the strongest one. | built, always on |
| 2 | Five scored hook candidates | Best of five, chosen by score. | built, always on |
| 3 | Five scored title candidates | Best of five, chosen by score. | built, always on |
| 4 | Context and takeaway lines | Labelled as editorial, never as tafsir. | built, `script.enabled` |
| 5 | Director's treatment | Emotional arc, palette and sound plan per story. | built, always on |
| 6 | Chapters in the description | Timestamped chapters for stories. | built, always on |
| 7 | Reflective comment question at the end | One honest question to invite comments; also in the description. | built, `look.comment_question` |
| 8 | Long stories split into parts | Each part stands alone under a minute. | built, always on |
| 9 | Next-part teaser | A line that points to the next part. | planned |
| 10 | Callback ending | The last line echoes the hook. | planned |

## Retention and reach

| # | Improvement | What it does | Status |
|---|---|---|---|
| 1 | Viral-style description and hashtags | Hook, call to action and up to 15 hashtags (choose the style). | built, `publishing.description_style` |
| 2 | Thumbnail studio | Three concepts from real frames, best one chosen. | built, always on |
| 3 | Topic variety window | Recent topics are not repeated. | built, always on |
| 4 | Auto-publish verified Quran videos | No review notice for verified ayah videos. | built, `review.auto_approve_quran` |
| 5 | Subtitle files for every video | SRT and VTT sidecars are written. | built, always on |
| 6 | Best-time scheduling from analytics | Post when your audience is awake. | planned |
| 7 | A/B title rotation | Swap titles after a few days and keep the winner. | planned |
| 8 | End-screen next-video card | Point viewers to the next short. | planned |
| 9 | Auto playlists by theme | Organise uploads automatically. | planned |
| 10 | Pinned comment with sources | Post the verification sources as the first comment. | planned |
