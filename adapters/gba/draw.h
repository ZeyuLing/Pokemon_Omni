#ifndef OMNI_GBA_DRAW_H
#define OMNI_GBA_DRAW_H
#include <stdint.h>
void omni_gba_box(int x,int y,int w,int h,uint16_t color);
void omni_gba_text(int x,int y,const char *text,uint16_t color,int end);
void omni_gba_small_text(int x,int y,const char *text,uint16_t color,int end);
unsigned omni_gba_small_text_width(const char *text);
void omni_gba_num(int x,int y,unsigned n,uint16_t color);
void omni_gba_picture(unsigned index,int x,int y);
void omni_game_dex_open_entry(uint32_t entry_id);
#endif
