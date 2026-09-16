# 🦖 PixelTube

A fully procedural **16+ pixel-animation factory** that runs on pure CPU.
Every frame is drawn by code, every sound is synthesized by code, and the
pixel voices are gibberish bleeps (Banjo-Kazooie style) with subtitles
translating what the characters "say". No GPU, no assets, no footage.

**The series:** mission-comedy agents – **Doris** the overconfident pink
dinosaur, **Rico** the greedy monkey, cowardly bunnies, snack-obsessed
gliders – cause their own problems in every episode.

**v6 – "The Six Laws" update (anime-retention research):**
1. **Cold opens** – every episode starts mid-chaos, never with intros
2. **Flaw engine** – plots are caused by personality (`story.FLAWS`), not luck
3. **Running mystery** – the red spiral & a silhouette ("The Watcher") hide in
   scenes (`mystery: true`), never explained
4. **Escalation tiers 1-5** – batch walks seeds up from petty crime to a
   shattered moon (T5 season finale)
5. **Cliffhanger endings** – final scene always opens the next question
6. **Show don't explain** – punchlines are animations: fire-breath 🔥,
   faceplants 🤕, shock-freezes 😱, power-poses 💪 (+ anger veins, dizzy
   stars, sweat drops, music notes as overlays)

New props: portal, torch, UFO, boulder, sword-in-stone – 22 total.
Full developer manual: **AGENTREAD.md**.

---

## Quick start

```bash
pip install -r requirements.txt

# Render one episode (pixel-bleep voices, no TTS needed)
python3 make_video.py --seed 77 --story 7 --scale 4 --backend none   # T5 finale!

# A whole season
python3 batch.py --count 10 --backend none

# With a local LLM writing the missions (Qwen via Ollama)
python3 make_video.py --llm --idea "a heist on the moon"
```

Output lands in `out/ep<seed>-<title>.mp4` (720p at `--scale 4`) with a
matching `.json` meta file ready for `upload_youtube.py`.

## How it works

| File | Role |
|---|---|
| `engine.py` | Procedural pixel renderer: 7 worlds, 18 props, character registry. **Same name = same character forever.** |
| `story.py` | Mission templates (English, mission-comedy) + a verb parser: the text IS the animation script (`"Rico ducked"` → duck, `"they sprinted together"` → both run). |
| `voice.py` | Gibberish pixel voices: one square-wave bleep per syllable, pitch locked per species (dino low, ape mid, bunny high). Deterministic per seed. |
| `sfx.py` | Synthesized movement SFX: alternating footsteps, jump-boing + landing thud, bonk, snore – looped in sync with the animation cycle. |
| `make_video.py` | Timeline assembly, subtitles (scene length = reading time), outro, mux via imageio-ffmpeg. |
| `script_llm.py` | Optional local QLLM (Qwen/Ollama) writes new missions in JSON. |
| `batch.py` | Season renderer. |
| `upload_youtube.py` | YouTube upload (OAuth), `selfDeclaredMadeForKids=False` (16+ content). |

## The cast

Doris, Boris, Leo, Nova, Trix, Puff, Milo, Zia (dinos) · Rico, Bosco (apes)
· Hops, Ash, Pix (bunnies). Unknown names get a deterministic hash identity.

```bash
python3 make_video.py --cast "doris,kanin" --story 0   # custom duo
python3 preview.py cast                                 # sprite sheet
```

## Steering an episode

* `--story N` – pick template (0–6) or let the seed choose
* `--seed N` – deterministic everything
* `--backend none` – pixel bleeps (default demo mode) · `--silent` – music+SFX only
* `--llm` / `--idea "..."` – let a local LLM write the mission

## License

MIT. Draw loud, render often. 🎬
