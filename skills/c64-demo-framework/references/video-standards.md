# NTSC and PAL: budgets, detection, music tempo

## The numbers

| | NTSC 6567R8 | NTSC 6567R56A (early) | PAL 6569 |
|---|---|---|---|
| Raster lines | 263 (`$000-$106`) | 262 (`$000-$105`) | 312 (`$000-$137`) |
| Cycles per line | 65 | 64 | 63 |
| **Cycles per frame** | **17095** | 16768 | **19656** |
| Frame rate | 59.83 Hz | 60.99 Hz | 50.12 Hz |
| CPU clock | 1022727 Hz | 1022727 Hz | 985248 Hz |
| Visible display window | lines 51-250 | same | lines 51-250 |

NTSC has **2561 fewer cycles a frame** than PAL (13% less). Code written and tested only on
PAL that uses more than ~87% of a frame will overrun on NTSC: the main loop misses a frame,
animation stutters, and raster splits land a frame late. Budget against NTSC unless the
project is explicitly PAL-only, and test with `x64sc -ntsc` first.

Those are *frame* lengths, not CPU time. With the display on, the 25 badlines take 40-43
cycles each (~1000 a frame) and every enabled sprite takes ~2 cycles per line it covers
(more at the start of each sprite line). Plan on roughly **16000 CPU cycles a frame on
NTSC and 18600 on PAL** with a text screen and no sprites, less with sprites. Measure the
real number with the `c64-vice-debugging` skill.

Raster lines that **do not exist on NTSC**: anything above `$106`. A `wait for line $120`
hangs an NTSC machine forever. Lines at 256 and above repeat the low byte of lines 0-55 on
PAL (256-311) and 0-6 on NTSC (256-262). So a `$D012`-only poll for a value under `$38`
matches **twice** a frame on PAL, and for `$00-$06` twice on NTSC too. Check bit 7 of
`$D011` as well, or pick a line in `$07-$FF` (line 250, `$FA`, is the usual choice).

## Detection at start-up

`templates/main.asm` → `detect_video`. With interrupts off, wait for raster bit 8 (`$D011`
bit 7), then record the highest `$D012` low byte seen until the raster wraps. PAL reaches
`$37`, NTSC `$06` (R56A `$05`). Anything under `$20` is NTSC. Keep the *maximum* rather
than the last read: the raster can wrap between reading `$D012` and testing bit 8.

Detection reads a Drean PAL-N machine (6572: 312 lines × 65 cycles = 20280 a frame,
50.4 Hz) as PAL. It has the most time per frame of all, so PAL code fits.

(Alternative: count cycles in one frame with a CIA timer. More code, same answer, and it
also tells the R56A apart.)

## PSID music made for PAL

Most PSID tunes are composed for one `play` call per 50 Hz frame (the PSID header's
`speed`/flags say so). Called once per 60 Hz NTSC frame, they run **20% fast**.

Pick one fix:

1. **Skip every sixth call on NTSC** (5 plays in 6 frames = 49.9 Hz). Cheapest, and it
   keeps everything frame-locked:
   ```kickass
   music_tick:              // call once per frame instead of music.play
       lda ntsc
       beq play             // PAL: every frame
       dec music_div        // NTSC: initialise music_div to 5
       bpl play
       lda #5
       sta music_div
       inc beat_hold        // tell beat-synced timers this frame was skipped
       rts
   play:
       jmp music.play       // (clear beat_hold at the top of each frame)
   ```
2. **Drive `play` from a CIA timer** at the PAL frame rate instead of the frame: 50.125 Hz
   is 19656 cycles on PAL and 20404 on NTSC. A CIA timer counts latch+1 cycles, so load
   19655 / 20403. Exact, but the music IRQ then
   drifts against your raster IRQs and can land in the middle of a split.

### Keeping beat-synced timing on the beat
If intro phases are counted in frames to land on the music's beats, slowing the tune on
NTSC (fix 1) leaves the frame counts finishing 20% early. Count in **music ticks**
instead: decrement duration counters only on frames where `play` actually ran (skip them
when `beat_hold` is set). Animation can still move every frame; only *when things change*
is locked to the tune.

## Things that differ besides timing
- **Sprite Y and the open bottom border**: on PAL, lines 256-311 repeat low bytes 0-55, so
  a sprite with Y < 56 is displayed twice once the border is open. NTSC has only lines
  256-262 there.
- **Colours**: the NTSC VIC's palette differs slightly (hue shifts in browns/oranges),
  so check colour choices on both.
- **Side-border and FLI tricks** are cycle-exact per line: code timed for 63-cycle PAL
  lines is wrong on 65-cycle NTSC lines and needs separate timing paths.
