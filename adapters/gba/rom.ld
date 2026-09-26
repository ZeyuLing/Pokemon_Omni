ENTRY(_start)
MEMORY {
 ROM (rx) : ORIGIN = 0x08000000, LENGTH = 32M
 EWRAM (rw) : ORIGIN = 0x02000000, LENGTH = 256K
 IWRAM (rwx) : ORIGIN = 0x03000000, LENGTH = 0x7e00
}
SECTIONS {
 .text : { KEEP(*(.gba_header)) *(.text*) *(.rodata*) . = ALIGN(4); } > ROM
 .ARM.exidx : { *(.ARM.exidx*) } > ROM
 .data : { __data_start = .; *(.data*) . = ALIGN(4); __data_end = .; } > EWRAM AT>ROM
 __data_load = LOADADDR(.data);
 /* Keep a ROM load image even in the standalone Dex without audio code.
  * An empty output section otherwise acquires an unusable objcopy LMA. */
 .iwram : { __iwram_start = .; *(.iwram*) LONG(0) . = ALIGN(4); __iwram_end = .; } > IWRAM AT>ROM
 __iwram_load = LOADADDR(.iwram);
 .bss (NOLOAD) : { __bss_start = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end = .; } > EWRAM
 /DISCARD/ : { *(.comment*) *(.ARM.attributes*) }
 ASSERT(__bss_end < 0x02040000, "EWRAM exceeded")
}
