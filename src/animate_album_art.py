#!/usr/bin/env python3
"""
animate_album_art.py

Scan a music library (mp3 / m4a / alac), extract embedded album art,
animate each *unique* piece of art with Stable Video Diffusion (local,
runs on an 8GB-class NVIDIA GPU), and write the result as MP4 files
mirroring the source folder structure. Also writes a Java-style
.properties file mapping each source audio file to its generated
animation.

Design notes
------------
- Dedup: identical cover art (by SHA-256 of the raw embedded image
  bytes) is only sent through the AI model once. The result is stored
  in a content-addressed cache folder:
      <output_root>/.generated/<hash[:2]>/<hash>.mp4
  For every audio file whose embedded art matches that hash, the
  script HARDLINKS (falls back to copy) that file into the mirrored
  location, e.g.:
      <output_root>/Artist/Album/01 Track.mp4
  Hardlinks share the same data on disk, so mirroring costs no extra
  space even though the same animation appears under many paths.

- Resume: a small JSON index at <output_root>/.generated/index.json
  tracks which hashes are already done, so re-running the script
  after an interruption skips completed work (unless --force).

- The properties file is rewritten from a merged in-memory dict each
  run, so re-running is safe and idempotent.

Usage
-----
  python animate_album_art.py \
      --source-dir "/path/to/music" \
      --output-dir "/path/to/animated_art" \
      --properties-file "/path/to/animated_art/mapping.properties"

  # Preview what would happen without loading any model / doing work:
  python animate_album_art.py --source-dir ... --output-dir ... --dry-run

See README.md for setup, VRAM tuning, and expected runtimes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# --- Optional progress bar -------------------------------------------------
try:
    from tqdm import tqdm
except ImportError:  # pragma: no cover - tqdm is a soft dependency
    def tqdm(iterable, **kwargs):
        return iterable

AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".alac"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("animate_album_art")


# =============================================================================
# Cover art extraction
# =============================================================================

@dataclass
class CoverArt:
    data: bytes
    mime: str  # e.g. "image/jpeg" or "image/png"

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


def extract_cover_art(path: Path) -> Optional[CoverArt]:
    """Extract the embedded cover art from an mp3/m4a/alac file, if present."""
    suffix = path.suffix.lower()
    try:
        if suffix == ".mp3":
            return _extract_from_id3(path)
        elif suffix in (".m4a", ".m4b", ".alac"):
            return _extract_from_mp4(path)
    except Exception as exc:  # noqa: BLE001 - log and continue scanning
        log.warning("Failed reading tags from %s: %s", path, exc)
    return None


def _extract_from_id3(path: Path) -> Optional[CoverArt]:
    from mutagen.id3 import ID3, APIC
    from mutagen.mp3 import MP3

    try:
        tags = ID3(path)
    except Exception:
        # Some files store ID3 via the MP3() wrapper instead
        audio = MP3(path)
        tags = audio.tags
        if tags is None:
            return None

    apics = tags.getall("APIC")
    if not apics:
        return None
    # Prefer the "front cover" APIC (type 3) if multiple are present
    best = next((a for a in apics if getattr(a, "type", None) == 3), apics[0])
    return CoverArt(data=best.data, mime=best.mime or "image/jpeg")


def _extract_from_mp4(path: Path) -> Optional[CoverArt]:
    from mutagen.mp4 import MP4, MP4Cover

    audio = MP4(path)
    covers = audio.tags.get("covr") if audio.tags else None
    if not covers:
        return None
    cover = covers[0]
    mime = "image/png" if cover.imageformat == MP4Cover.FORMAT_PNG else "image/jpeg"
    return CoverArt(data=bytes(cover), mime=mime)


# =============================================================================
# Filesystem helpers
# =============================================================================

def scan_audio_files(source_dir: Path):
    for p in sorted(source_dir.rglob("*")):
        if p.is_file() and p.suffix.lower() in AUDIO_EXTENSIONS:
            yield p


def link_or_copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        dst.unlink()
    try:
        os.link(src, dst)
    except OSError:
        # Cross-device link, unsupported filesystem, etc.
        shutil.copy2(src, dst)


def mirrored_output_path(output_root: Path, source_root: Path, audio_file: Path) -> Path:
    rel = audio_file.relative_to(source_root).with_suffix(".mp4")
    return output_root / rel


def cache_path_for_hash(output_root: Path, digest: str) -> Path:
    return output_root / ".generated" / digest[:2] / f"{digest}.mp4"


# =============================================================================
# Generation index (resume support)
# =============================================================================

class GenerationIndex:
    """Tracks which content hashes have already been animated."""

    def __init__(self, output_root: Path):
        self.path = output_root / ".generated" / "index.json"
        self.data: dict[str, dict] = {}
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
            except Exception as exc:  # noqa: BLE001
                log.warning("Could not read existing index %s: %s", self.path, exc)

    def is_done(self, digest: str, cache_file: Path) -> bool:
        entry = self.data.get(digest)
        return bool(entry) and entry.get("status") == "done" and cache_file.exists()

    def mark_done(self, digest: str, cache_file: Path):
        self.data[digest] = {"status": "done", "path": str(cache_file)}
        self.save()

    def mark_failed(self, digest: str, error: str):
        self.data[digest] = {"status": "failed", "error": error}
        self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, indent=2))


# =============================================================================
# Properties file (Java-style key=value mapping)
# =============================================================================

def escape_properties_value(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("=", "\\=")
        .replace(":", "\\:")
        .replace("\n", "\\n")
    )


class PropertiesFile:
    def __init__(self, path: Path):
        self.path = path
        self.entries: dict[str, str] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    self.entries[k] = v

    def set(self, source_audio: Path, generated_mp4: Path):
        key = escape_properties_value(str(source_audio))
        value = escape_properties_value(str(generated_mp4))
        self.entries[key] = value

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["# source_audio_file=generated_animation_file", "# auto-generated by animate_album_art.py"]
        for k, v in sorted(self.entries.items()):
            lines.append(f"{k}={v}")
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# =============================================================================
# Stable Video Diffusion wrapper
# =============================================================================

class Animator:
    """Lazily loads Stable Video Diffusion and animates a still image."""

    def __init__(
        self,
        model_id: str,
        width: int,
        height: int,
        num_frames: int,
        fps: int,
        motion_bucket_id: int,
        noise_aug_strength: float,
        decode_chunk_size: int,
        seed: Optional[int],
    ):
        self.model_id = model_id
        self.width = width
        self.height = height
        self.num_frames = num_frames
        self.fps = fps
        self.motion_bucket_id = motion_bucket_id
        self.noise_aug_strength = noise_aug_strength
        self.decode_chunk_size = decode_chunk_size
        self.seed = seed
        self._pipe = None

    def _load(self):
        if self._pipe is not None:
            return
        import torch
        from diffusers import StableVideoDiffusionPipeline

        log.info("Loading model %s (first run only, this can take a while)...", self.model_id)
        pipe = StableVideoDiffusionPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16,
            variant="fp16",
        )
        # Keeps peak VRAM low enough for 8GB cards by streaming submodules
        # between CPU and GPU as needed.
        pipe.enable_model_cpu_offload()
        self._pipe = pipe

    @staticmethod
    def _pad_square_to_canvas(square_img, canvas_w: int, canvas_h: int):
        """Center a square image on a wider canvas, filling the sides with a
        blurred, stretched copy of the same image so the model doesn't see
        a harsh black border (which tends to produce ugly edge artifacts)."""
        from PIL import Image, ImageFilter

        square_img = square_img.convert("RGB")
        side = min(canvas_w, canvas_h)
        fg = square_img.resize((side, side), Image.LANCZOS)

        bg = square_img.resize((canvas_w, canvas_h), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=canvas_w // 20))

        canvas = bg.copy()
        offset = ((canvas_w - side) // 2, (canvas_h - side) // 2)
        canvas.paste(fg, offset)
        return canvas, offset, side

    def animate(self, image_bytes: bytes) -> list:
        """Returns a list of PIL frames (square, cropped back from the
        padded canvas the model actually ran on)."""
        import io
        import torch
        from PIL import Image

        self._load()

        src = Image.open(io.BytesIO(image_bytes))
        canvas, offset, side = self._pad_square_to_canvas(src, self.width, self.height)

        generator = None
        if self.seed is not None:
            generator = torch.manual_seed(self.seed)

        result = self._pipe(
            canvas,
            height=self.height,
            width=self.width,
            num_frames=self.num_frames,
            decode_chunk_size=self.decode_chunk_size,
            motion_bucket_id=self.motion_bucket_id,
            noise_aug_strength=self.noise_aug_strength,
            generator=generator,
        )
        frames = result.frames[0]

        ox, oy = offset
        cropped = [f.crop((ox, oy, ox + side, oy + side)) for f in frames]
        return cropped


def add_boomerang(frames: list) -> list:
    """Forward + reverse (minus duplicated endpoints) for a seamless loop."""
    if len(frames) < 2:
        return frames
    return frames + frames[-2:0:-1]


def export_mp4(frames: list, dest: Path, fps: int):
    from diffusers.utils import export_to_video

    dest.parent.mkdir(parents=True, exist_ok=True)
    # export_to_video writes via imageio/ffmpeg; produces a standard H.264 mp4
    export_to_video(frames, str(dest), fps=fps)


# =============================================================================
# Main
# =============================================================================

@dataclass
class Stats:
    audio_files: int = 0
    no_art: int = 0
    unique_art: int = 0
    generated: int = 0
    skipped_existing: int = 0
    failed: int = 0
    linked: int = 0


def parse_args(argv=None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source-dir", required=True, type=Path, help="Root directory of your audio library")
    p.add_argument("--output-dir", required=True, type=Path, help="Root directory to write animated art into (configurable)")
    p.add_argument("--properties-file", type=Path, default=None,
                   help="Path to the .properties mapping file (default: <output-dir>/mapping.properties)")

    p.add_argument("--model-id", default="stabilityai/stable-video-diffusion-img2vid",
                   help="Diffusers model id. Use the '-xt' variant for 25 frames if you have VRAM/time to spare.")
    p.add_argument("--width", type=int, default=1024, help="Model canvas width (SVD native: 1024)")
    p.add_argument("--height", type=int, default=576, help="Model canvas height (SVD native: 576)")
    p.add_argument("--num-frames", type=int, default=14, help="Frames to generate (14 for base model, 25 for -xt)")
    p.add_argument("--fps", type=int, default=7, help="Playback fps of the output mp4")
    p.add_argument("--motion-bucket-id", type=int, default=127, help="Higher = more motion (SVD parameter)")
    p.add_argument("--noise-aug-strength", type=float, default=0.02, help="Higher = more deviation from source image")
    p.add_argument("--decode-chunk-size", type=int, default=2, help="Lower uses less VRAM during frame decoding")
    p.add_argument("--seed", type=int, default=None, help="Fix a seed for reproducible animations")
    p.add_argument("--boomerang", dest="boomerang", action="store_true", default=True,
                   help="Play forward then reverse for a seamless loop (default: on)")
    p.add_argument("--no-boomerang", dest="boomerang", action="store_false")

    p.add_argument("--force", action="store_true", help="Regenerate even if a cached animation already exists")
    p.add_argument("--dry-run", action="store_true", help="Only scan and report; do not load the model or generate anything")
    p.add_argument("--limit", type=int, default=None, help="Only process the first N unique artworks (useful for testing)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    source_dir: Path = args.source_dir.resolve()
    output_dir: Path = args.output_dir.resolve()
    properties_path: Path = (args.properties_file or (output_dir / "mapping.properties")).resolve()

    if not source_dir.is_dir():
        log.error("Source dir does not exist: %s", source_dir)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = Stats()
    props = PropertiesFile(properties_path)
    index = GenerationIndex(output_dir)

    # ---- Pass 1: scan & group by content hash ----
    audio_files = list(scan_audio_files(source_dir))
    stats.audio_files = len(audio_files)
    log.info("Found %d audio files under %s", stats.audio_files, source_dir)

    by_hash: dict[str, list[Path]] = {}
    art_by_hash: dict[str, CoverArt] = {}

    for audio_file in tqdm(audio_files, desc="Scanning tags"):
        art = extract_cover_art(audio_file)
        if art is None:
            stats.no_art += 1
            continue
        by_hash.setdefault(art.sha256, []).append(audio_file)
        art_by_hash.setdefault(art.sha256, art)

    stats.unique_art = len(by_hash)
    log.info(
        "%d files have embedded art (%d unique images, %d have no art)",
        stats.audio_files - stats.no_art, stats.unique_art, stats.no_art,
    )

    if args.dry_run:
        log.info("Dry run: no model loaded, nothing generated.")
        _print_summary(stats)
        return 0

    animator = Animator(
        model_id=args.model_id,
        width=args.width,
        height=args.height,
        num_frames=args.num_frames,
        fps=args.fps,
        motion_bucket_id=args.motion_bucket_id,
        noise_aug_strength=args.noise_aug_strength,
        decode_chunk_size=args.decode_chunk_size,
        seed=args.seed,
    )

    hashes = list(by_hash.keys())
    if args.limit:
        hashes = hashes[: args.limit]

    for digest in tqdm(hashes, desc="Animating unique artworks"):
        cache_file = cache_path_for_hash(output_dir, digest)

        if not args.force and index.is_done(digest, cache_file):
            stats.skipped_existing += 1
        else:
            try:
                frames = animator.animate(art_by_hash[digest].data)
                if args.boomerang:
                    frames = add_boomerang(frames)
                export_mp4(frames, cache_file, fps=args.fps)
                index.mark_done(digest, cache_file)
                stats.generated += 1
            except Exception as exc:  # noqa: BLE001
                log.error("Failed to animate hash %s: %s", digest, exc)
                index.mark_failed(digest, str(exc))
                stats.failed += 1
                continue

        # Link into every mirrored location that uses this artwork
        for audio_file in by_hash[digest]:
            dest = mirrored_output_path(output_dir, source_dir, audio_file)
            try:
                link_or_copy(cache_file, dest)
                props.set(audio_file, dest)
                stats.linked += 1
            except Exception as exc:  # noqa: BLE001
                log.error("Failed to link %s -> %s: %s", cache_file, dest, exc)

        props.save()  # incremental save so a crash mid-run doesn't lose progress

    _print_summary(stats)
    log.info("Properties file written to %s", properties_path)
    return 0


def _print_summary(stats: Stats):
    log.info(
        "Summary: %d audio files | %d without art | %d unique artworks | "
        "%d generated | %d skipped (already done) | %d failed | %d mirrored links written",
        stats.audio_files, stats.no_art, stats.unique_art,
        stats.generated, stats.skipped_existing, stats.failed, stats.linked,
    )


if __name__ == "__main__":
    sys.exit(main())
