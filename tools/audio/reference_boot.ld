ENTRY(_start)
SECTIONS {
 . = 0x080000c0;
 .text : { KEEP(*(.entry)) *(.text*) *(.rodata*) }
 /DISCARD/ : { *(.ARM.exidx*) *(.comment*) *(.ARM.attributes*) }
 ASSERT(. < 0x080002f0, "Reference entry overlaps song selector")
}
