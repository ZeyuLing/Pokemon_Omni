#include "omni/battlefield.h"
#define CHECK(x) do { if (!(x)) return __LINE__; } while (0)
int main(void) {
 OmniWarActor a[3]={
  {.x=100,.tx=100,.y=80,.ty=80,.team=0,.target=1,.attack=1,.stop=65535},
  {.x=40,.tx=40,.y=80,.ty=80,.team=1,.target=0,.attack=1,.stop=100},
  {.x=160,.tx=160,.y=80,.ty=80,.team=1,.target=0,.attack=1,.stop=65535}
 };
 OmniWarPose p[3];
 omni_war_sample_all(a,3,0,p);
 CHECK(p[0].face==2); /* Team 0 must also be able to attack left. */
 CHECK(p[1].face==3&&p[2].face==2);
 omni_war_sample_all(a,3,100,p);
 CHECK(p[0].face==3); /* Surviving target is now on the other side. */
 CHECK(p[1].action==OMNI_WAR_DOWN);
 a[0].tx=60;a[0].duration=100;
 omni_war_sample_all(a,3,30,p);CHECK(p[0].face==2);
 a[0].tx=140;
 omni_war_sample_all(a,3,30,p);CHECK(p[0].face==3);
 a[0].tx=100;a[0].ty=120;
 omni_war_sample_all(a,3,30,p);CHECK(p[0].face==0);
 a[0].ty=40;
 omni_war_sample_all(a,3,30,p);CHECK(p[0].face==1);
 a[0].duration=0;a[0].ty=80;a[0].target=2;
 a[2].tx=100;a[2].ty=160;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==0);
 a[2].ty=32;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==1);
 a[2].tx=140;a[2].ty=120;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==5);
 a[2].tx=60;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==4);
 a[2].ty=40;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==6);
 a[2].tx=140;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==7);
 a[0].attack=0;
 omni_war_sample_all(a,3,0,p);CHECK(p[0].face==3); /* Human support has cardinal art. */
 return 0;
}
