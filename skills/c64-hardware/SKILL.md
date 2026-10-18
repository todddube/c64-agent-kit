---
name: c64-hardware
description: Register-level reference for the Commodore 64 - memory map and $01 bank switching, zero page ownership, VIC-II ($D000-$D02E, $D018 screen/charset mapping, VIC banks via $DD00, sprites, display modes, raster and badline timing on NTSC and PAL), SID ($D400) voices, envelopes and filter, CIA 1/2 timers, interrupts, NMI and the keyboard matrix, plus 6502/6510 addressing modes, cycle counts and NMOS pitfalls. Use WHENEVER C64 code touches a hardware address, when graphics come out as garbage, the screen is blank, sprites are missing, the SID is silent, an IRQ locks up, or you need a cycle count or a register's bits. Read the reference instead of recalling addresses from memory.
---

# C64 hardware reference

Don't recall register bits from memory: open the reference file that covers the question.
Each one is short and table-driven.

| File | Covers |
|---|---|
| `references/memory-map.md` | full address map, `$00/$01` CPU port and bank configurations, zero page ownership (what is safe to use), free RAM, clean-exit sequence |
| `references/vic-ii.md` | `$D000-$D02E` bit by bit, VIC bank select via `$DD00`, `$D018` screen/charset/bitmap mapping, character ROM shadows at `$1000`/`$9000`, display modes, sprites and pointers, raster/badline timing on NTSC and PAL, DEN blanking |
| `references/sid-cia.md` | SID voices, ADSR, gate handling, filter and volume; CIA 1/2 ports, timers, interrupt control; IRQ vs NMI; the full keyboard matrix; RESTORE |
| `references/6502.md` | addressing modes with cycle counts, page-cross penalties, flags, signed and 8.8 fixed-point idioms, NMOS 6502 pitfalls (`jmp ($xxFF)`, decimal mode, RMW double writes) |

## The ten facts that cause most C64 bugs

1. **Character ROM shadow**: in VIC banks 0 and 2, the VIC sees character ROM at
   `$1000-$1FFF` / `$9000-$9FFF` whatever RAM holds there. Graphics data there is invisible
   to the VIC.
2. **VIC bank** = `$DD00` bits 0-1, **inverted** (`%11` = bank 0 at `$0000`). Set DDR
   `$DD02` bits 0-1 to output, and change only bits 0-1 of `$DD00` (read, `and #$fc`,
   `ora`): the other bits are serial bus lines. `$D018` addresses are *within* the bank.
3. **Sprite pointers** live at screen + `$3F8`; value = (data address within bank) / 64.
4. **Raster IRQ** must be acknowledged (`$D019`) or it fires forever. Bit 8 of the raster
   compare is `$D011` bit 7.
5. **NTSC has 263 lines** (`$000-$106`) and 65 cycles a line: 17095 cycles a frame against
   PAL's 19656. Waiting for a line above `$106` hangs an NTSC machine.
6. **Badlines** (every 8th line in the display window when DEN is on) steal 40-43 cycles;
   sprites steal more. Budget per line, not per frame, for raster effects.
7. **`sei` does not mask NMI.** CIA 2 (`$DD0D`) and the RESTORE key both raise NMI; RESTORE
   cannot be masked at the CIA; most simply, point the NMI vector at an `rti`. (Leaving a
   CIA 2 NMI unacknowledged also blocks it: /NMI is edge-triggered and stays low.)
8. **`$01`**: bits 0-2 select ROM/IO banking. Keep bits 3-5 as they are, and `sei` before
   banking out the KERNAL. The CPU always takes IRQs through `$FFFE`; with the KERNAL in,
   that is the ROM handler, which jumps through `$0314`. With it out, `$FFFE` is RAM and
   must point at your handler.
9. **Color RAM** `$D800-$DBFF` is 4 bits wide: the upper nibble reads back as noise.
10. **SID registers are write-only** (except `$D419-$D41C`): keep shadow copies, never
    read-modify-write.

## Related skills
- `c64-demo-framework`: a tested machine-takeover skeleton, NTSC/PAL detection, borders, music tempo.
- `c64-code-review`: the checklist that turns these facts into a review.
- `c64-vice-debugging`: confirm a hardware suspicion in the emulator (`io d000`, raster conditions).
