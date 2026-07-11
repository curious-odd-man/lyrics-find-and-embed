# Album Art Animator

Scans an audio library (`.mp3`, `.m4a`/ALAC), extracts embedded cover art,
animates each **unique** piece of art with Stable Video Diffusion (runs
locally on your GPU), and writes MP4 clips that mirror your source folder
structure — plus a `.properties` file mapping every audio file to its
generated animation.

## How it fits together

```
music/Artist/Album/01 Track.mp3   --(scan + hash cover art)-->  sha256
                                                                    |
                                                                    v
output/.generated/ab/ab12...ef.mp4   <-- generated ONCE per unique hash
                                                                    |
                                                                    | hardlink (free, no extra disk space)
                                                                    v
output/Artist/Album/01 Track.mp4   <-- what your player actually opens

output/mapping.properties:
  /music/Artist/Album/01 Track.mp3=/output/Artist/Album/01 Track.mp4
```

If ten tracks on an album share the same cover, the AI model runs **once**
for that album, not ten times. The ten mirrored `.mp4` files are hardlinks
to the same data, so dedup and a "browsable" mirrored tree both apply.

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate

# Install PyTorch matching your CUDA version FIRST (check https://pytorch.org
# for the right command for your driver — e.g. for CUDA 12.1:)
pip install torch --index-url https://download.pytorch.org/whl/cu121

# Then everything else
pip install -r requirements.txt
```

You'll also need ~10GB of free disk for the model weights (downloaded
automatically from Hugging Face the first time you run the script).

**8GB VRAM notes:**

- The script uses `enable_model_cpu_offload()` and a small `decode_chunk_size`
  by default, which keeps peak VRAM usage well under 8GB at the cost of
  some speed (submodules are streamed CPU<->GPU as needed).
- Default settings use the base `img2vid` model (14 frames) rather than
  the `-xt` variant (25 frames) — noticeably faster and lighter, still
  gives a ~2 second loop (4s with boomerang) at 7fps.
- Expect roughly 30–90 seconds per **unique** artwork on an 8GB card
  (e.g. RTX 3070/4060-class). This only runs once per unique cover, not
  once per track — check `--dry-run` first to see how many unique images
  you actually have.

## 2. Preview before committing GPU time

```bash
python animate_album_art.py  --source-dir "/path/to/music"  --output-dir "/path/to/animated_art"  --dry-run
```

This scans everything, extracts/hashes cover art, and reports how many
audio files, how many are missing art, and — the number that matters —
how many **unique** images will actually need to be animated. No model is
loaded during a dry run.

## 3. Run for real

```bash
python animate_album_art.py   --source-dir "/path/to/music"   --output-dir "/path/to/animated_art"
```

- Re-running the same command later only processes new/changed music —
  already-generated artwork is detected via `output/.generated/index.json`
  and skipped. Use `--force` to regenerate everything anyway.
- `--limit N` processes only the first N unique artworks — handy for a
  quick test before committing to a multi-hour run on a large library.
- The `.properties` file is rewritten from a merged, sorted dict every
  run, so it's safe to re-run repeatedly.

## 4. Useful flags

| Flag                   | Default                                      | Notes                                                                                     |
|------------------------|----------------------------------------------|-------------------------------------------------------------------------------------------|
| `--properties-file`    | `<output-dir>/mapping.properties`            | override mapping file location                                                            |
| `--model-id`           | `stabilityai/stable-video-diffusion-img2vid` | swap for the `-xt` (25-frame) variant if you have VRAM/time to spare                      |
| `--num-frames`         | 14                                           | raise if using `-xt`                                                                      |
| `--fps`                | 7                                            | SVD is trained near this fps; raising it just speeds up playback of the same frames       |
| `--motion-bucket-id`   | 127                                          | higher = more motion; try 40–80 for subtler "breathing" album art, 150+ for lively motion |
| `--noise-aug-strength` | 0.02                                         | higher = more the model deviates from the source image                                    |
| `--no-boomerang`       | (boomerang on)                               | disable forward+reverse looping, just use the raw forward clip                            |
| `--seed`               | random                                       | fix for reproducible results while tuning motion settings                                 |
| `--decode-chunk-size`  | 2                                            | lower = less VRAM during decode, slower                                                   |

## 5. Properties file format

Standard Java-style `key=value`, one entry per audio file, with `=`, `:`,
`\`, and newlines escaped in both key and value:

```properties
# source_audio_file=generated_animation_file
/music/Pink Floyd/The Wall/01 In The Flesh.mp3=/animated_art/Pink Floyd/The Wall/01 In The Flesh.mp4
/music/Pink Floyd/The Wall/02 The Thin Ice.mp3=/animated_art/Pink Floyd/The Wall/02 The Thin Ice.mp4
```

Your player can load this at startup to know, for any given audio file
path, exactly which animated file to display instead of the static
embedded art.

## 6. Tuning motion look

Album art usually looks best with **subtle** motion rather than the
dramatic movement SVD is often used for (it was trained mostly on
natural video). Good starting point for a "living photo" feel:

```bash
--motion-bucket-id 60 --noise-aug-strength 0.01
```

Increase `motion-bucket-id` gradually (try 80, 100, 127...) if you want
more visible movement, and use `--seed` while comparing so you're
changing one variable at a time.
