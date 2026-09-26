/* Offline reference ROM entry: preserve the archived ROM's sound functions,
 * run each once per hardware VBlank. This is not linked into the game. */
#include <stdint.h>
#define REG16(a) (*(volatile uint16_t*)(a))
__attribute__((section(".entry"),naked,target("arm"))) void _start(void){
 __asm__ volatile("ldr sp, =0x03007f00\nldr r0, =boot\nbx r0");
}
__attribute__((used)) void boot(void){
 void (*init)(void)=(void*)0x08527b05;
 void (*select)(uint16_t)=(void*)0x08527bc5;
 void (*main_sound)(void)=(void*)0x08527bb9;
 void (*vsync)(void)=(void*)0x085274a5;
 REG16(0x04000208)=0;REG16(0x04000000)=0x80;
 init();select(REG16(0x080002f0));
 for(;;){
  while(REG16(0x04000006)>=160){}
  while(REG16(0x04000006)<160){}
  vsync();main_sound();
 }
}
