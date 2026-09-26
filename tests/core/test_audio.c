#include "omni/audio.h"
static unsigned failure;
#define CHECK(x) do{if(!(x)){failure=__LINE__;return 0;}}while(0)
unsigned audio_failure_line(void){return failure;}
unsigned audio_test(void){
 uint8_t b[132]={0};int16_t out[256];unsigned i;
 omni_audio_decode(b,out);for(i=0;i<256;++i)CHECK(out[i]==0);
 b[4]=0x77;b[5]=0xff;omni_audio_decode(b,out);
 CHECK(out[0]==0&&out[1]==11&&out[2]==41&&out[3]==-22&&out[4]==-158&&out[5]==-139);
 b[0]=0xf8;b[1]=0x7f;b[2]=255;b[4]=0x77;omni_audio_decode(b,out);
 CHECK(out[0]==32760&&out[1]==32767&&out[2]==32767);
 b[0]=8;b[1]=0x80;b[2]=88;b[4]=0xff;omni_audio_decode(b,out);
 CHECK(out[0]==-32760&&out[1]==-32768&&out[2]==-32768);
 return 1;
}
