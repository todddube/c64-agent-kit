// <name> - Commodore 64 demo skeleton
// KickAssembler v5.x. Build: python3 <c64-toolchain>/scripts/c64.py build main.asm
//
// What this skeleton already does, so a new demo starts from known-good ground:
//   - takes over the machine: sei, CIA 1 IRQs and CIA 2 NMIs masked and acked,
//     NMI vector -> rti so RUN/STOP+RESTORE cannot warm-start BASIC over our
//     zero page
//   - detects NTSC (263 lines, 17095 cycles/frame) or PAL (312, 19656) once
//   - a frame loop locked to raster line 250, which exists on both standards
//   - RUN/STOP exits through the KERNAL RESET vector (never rts to BASIC)
//
// Memory:
//   $02-$03     zero page: ntsc, frame
//   $0400       screen (bank 0 default)
//   $0810-      code (after the BasicUpstart2 stub at $0801)

.label VIC_CONTROL1 = $d011     // bit 7 = raster bit 8, bit 4 = DEN
.label VIC_RASTER   = $d012
.label BORDER       = $d020
.label BACKGROUND   = $d021
.label SPRITE_ON    = $d015
.label SID          = $d400
.label CIA1_PRA     = $dc00     // keyboard row select
.label CIA1_PRB     = $dc01     // keyboard column read
.label CIA1_DDRA    = $dc02
.label CIA1_DDRB    = $dc03
.label CIA1_ICR     = $dc0d
.label CIA2_ICR     = $dd0d
.label NMI_VECTOR   = $0318     // KERNAL banked in: its NMI entry jumps through here
.label SCREEN       = $0400

.label ntsc         = $02       // nonzero on an NTSC VIC
.label frame        = $03       // counts frames, wraps

BasicUpstart2(start)

* = $0810 "Code"
start:
    sei
    ldx #$ff                    // known stack, in case of a restart jump
    txs
    cld

    lda #$7f                    // CIA 2: mask its NMI sources, ack pending
    sta CIA2_ICR
    lda CIA2_ICR
    lda #$7f                    // CIA 1: same for its timer IRQs
    sta CIA1_ICR
    lda CIA1_ICR

    // RESTORE is wired to /NMI directly, not through CIA 2, so $dd0d cannot
    // stop it. Take the vector instead. nmi_ignore is placed at an address
    // whose low byte is $47, the same as the KERNAL default ($fe47), so one
    // store switches the vector atomically: a RESTORE press between two
    // separate stores would jump to a half-written address.
    lda #>nmi_ignore
    sta NMI_VECTOR + 1

    lda #$ff                    // keyboard: port A drives rows,
    sta CIA1_DDRA
    lda #$00                    // port B reads columns
    sta CIA1_DDRB

    jsr detect_video

    // --- demo setup goes here ---
    lda #$00
    sta BORDER
    sta BACKGROUND
    sta frame
    jsr clear_screen
    jsr show_standard

main_loop:
    jsr wait_frame
    // --- per-frame work goes here. Budget: 17095 cycles a frame on NTSC,
    //     minus ~1000 for badlines and more for sprite DMA: plan on ~16000.
    //     Calling a PAL PSID tune here once a frame plays it 20% fast on
    //     NTSC - see the skill's references/video-standards.md.
    inc frame
    jsr check_exit
    jmp main_loop

//------------------------------------------------------------------
// wait_frame - return once per frame, as the raster leaves line 250.
// Line 250 exists on NTSC (0-262) and PAL (0-311), and its low byte
// $fa occurs once per frame on both. Waiting to *leave* the line stops
// a short frame's work from running twice on the same line.
//------------------------------------------------------------------
wait_frame:
    lda #$fa
!:  cmp VIC_RASTER
    bne !-
!:  cmp VIC_RASTER
    beq !-
    rts

//------------------------------------------------------------------
// detect_video - ntsc = 1 on NTSC, 0 on PAL. Interrupts off.
// Runs the raster into its 9th bit and keeps the highest low byte seen:
// NTSC 6567R8 tops out at line $106 (R56A at $105), PAL 6569 at $137
// (PAL-N 6572, Drean, also reads as PAL). Under $20 is NTSC. The max is
// kept, not the last read, because the raster can wrap to line 0 between
// reading $d012 and testing bit 8. Waiting to be below line 256 first
// means tracking always starts at line $100: entering on the last cycles
// of PAL line $137 would otherwise see only line 0 and report NTSC.
//------------------------------------------------------------------
detect_video:
    lda #$00
    sta ntsc                    // scratch: highest low byte seen
!:  bit VIC_CONTROL1
    bmi !-                      // wait until below line 256
!wait:
    bit VIC_CONTROL1
    bpl !wait-                  // wait for line 256+
!track:
    lda VIC_RASTER
    cmp ntsc
    bcc !+
    sta ntsc
!:  bit VIC_CONTROL1
    bmi !track-                 // until the raster wraps to line 0
    lda ntsc
    ldx #$00
    cmp #$20
    bcs !+                      // PAL
    inx                         // NTSC
!:  stx ntsc
    rts

clear_screen:
    lda #$20                    // screen code: space
    ldx #$00
!:  sta SCREEN, x
    sta SCREEN + $100, x
    sta SCREEN + $200, x
    sta SCREEN + $2e8, x        // last page overlaps; stops short of $07f8
    inx
    bne !-
    rts

// Write "NTSC" or "PAL" at the top left, in light blue (color RAM).
show_standard:
    ldy #$00
    lda ntsc
    beq !+
    ldy #label_ntsc - labels
!:  ldx #$00
!:  lda labels, y
    sta SCREEN, x
    lda #$0e
    sta $d800, x
    iny
    inx
    cpx #4
    bne !-
    rts

.encoding "screencode_upper"
labels:
    .text "PAL "
label_ntsc:
    .text "NTSC"

//------------------------------------------------------------------
// check_exit - RUN/STOP (row 7, column bit 7, active low) quits.
//------------------------------------------------------------------
check_exit:
    lda #$7f
    sta CIA1_PRA
    lda CIA1_PRB
    and #$80
    beq exit_demo               // bit clear = pressed
    lda #$ff
    sta CIA1_PRA
    rts

// The program has overwritten BASIC's zero page, so it cannot rts back.
// Put the hardware back and go through the KERNAL RESET vector.
exit_demo:
    lda #$00
    ldx #$18
!:  sta SID, x                  // silence the SID
    dex
    bpl !-
    sta SPRITE_ON
    lda #$1b                    // display on, 25 rows, text mode
    sta VIC_CONTROL1
    lda #$2f                    // default CPU port direction
    sta $00
    lda #$37                    // default ROM banking (if a demo changed it)
    sta $01
    lda #$ff
    sta CIA1_PRA
                                // NO cli: $fffc does its own sei, and an IRQ
                                // taken in between would run the KERNAL
                                // handler on our zero page
    jmp ($fffc)

// Pad to the next address with low byte $47 (costs up to 255 bytes; put
// tables in front of this to use the gap).
    .fill ($47 - <*) & $ff, 0
nmi_ignore:
    .errorif (nmi_ignore & $ff) != $47, "nmi_ignore must sit at $xx47"
    rti
