#include <stddef.h>
#include <stdint.h>
void *memset(void *d,int value,size_t n){uint8_t *p=d;while(n--)*p++=(uint8_t)value;return d;}
void *memcpy(void *d,const void *s,size_t n){uint8_t *p=d;const uint8_t *q=s;while(n--)*p++=*q++;return d;}
int memcmp(const void *a,const void *b,size_t n){const uint8_t *p=a,*q=b;while(n--){if(*p!=*q)return *p-*q;++p;++q;}return 0;}
