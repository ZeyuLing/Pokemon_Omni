ENTRY(_start)
MEMORY {
 ROM (rx) : ORIGIN = 0x08000000, LENGTH = 32M
 EWRAM (rw) : ORIGIN = 0x02000000, LENGTH = 256K
}
SECTIONS {
 .text : { KEEP(*(.gba_header)) *(.text*) *(.rodata*) . = ALIGN(4); } > ROM
 .ARM.exidx : { *(.ARM.exidx*) } > ROM
 .data : { __data_start = .; *(.data*) . = ALIGN(4); __data_end = .; } > EWRAM AT>ROM
 __data_load = LOADADDR(.data);
 .bss (NOLOAD) : { __bss_start = .; *(.bss*) *(COMMON) . = ALIGN(4); __bss_end = .; } > EWRAM
 /DISCARD/ : { *(.comment*) *(.ARM.attributes*) }
 ASSERT(__bss_end < 0x02040000, "EWRAM exceeded")
}
