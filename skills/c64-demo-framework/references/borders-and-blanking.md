# Opening the top/bottom border, and blanking the screen

## Opening the vertical border

The VIC sets its vertical-border flip-flop on the first line of the bottom border: line
251 with RSEL=1 (`$D011` bit 3, 25 rows), line 247 with RSEL=0 (24 rows). Switch to 24
rows **while the raster is on line 250** and the line it now waits for (247) is already
past. The flip-flop is never set: there is no bottom border that frame and no top border
on the next, and sprites are displayed through both. Switch back to 25 rows any time after
line 251, so the next frame can do it again:

```kickass
main_loop:
    lda #$fa                    // sync on line 250
!:  cmp $d012
    bne !-
    lda #$13                    // RSEL=0 (keep DEN and YSCROLL=3): border never closes
    sta $d011
    // ... a frame's worth of work; the raster ends up well past 251 ...
    lda #$1b                    // back to 25 rows for the next pass
    sta $d011
    jmp main_loop
```
Line 250 exists on NTSC and PAL alike, so this works on both. A raster IRQ on line 250 is
the more robust version of the same thing.

Two costs, both easy to miss:
- **The VIC shows the last byte of its bank in the open border** (`$3FFF` in bank 0,
  `$39FF` with ECM). In the open border it is idle and fetches that byte, not the screen,
  so whatever junk it holds tiles the whole border. Zero it, or set it on purpose.
- **Sprites with Y < 56 get a ghost twin on PAL.** A sprite starts when the low 8 bits of
  the raster match its Y, and PAL lines 256-311 repeat low bytes 0-55, which become visible
  once the bottom border is open. Keep sprite Y ≥ 56. In practice you gain the bottom
  border, not the top.

The **side** borders are a different problem: they need a cycle-exact `$D016` write (38/40
columns) on every raster line, so a stable-raster IRQ that eats most of the frame, with
separate timing for 63-cycle PAL and 65-cycle NTSC lines.

## Blanking the screen (intros and reveals)

Clearing DEN (`$D011` bit 4: write `$0B` instead of `$1B`) switches the whole display off:
text and colour RAM vanish, and sprites are hidden because the border now covers the whole
screen. What is left is a flat sheet of border colour. While DEN is off there are no
badlines, but **sprite DMA still runs**: clear `$D015` too if you want every cycle (65 a
line on NTSC, 63 on PAL).

To switch modes or redraw without the viewer seeing it:
1. Set border and background to the same colour, so nothing flickers when DEN comes back.
2. Clear DEN.
3. Switch VIC bank, `$D018`, `$D016`, and draw the new screen into memory nobody can see.
4. Set DEN again before line `$30` of the frame that should show the picture (for
   example from the bottom of the previous frame, line 250 onwards).

The VIC checks DEN on line `$30`: setting it after that takes effect on the next frame.
