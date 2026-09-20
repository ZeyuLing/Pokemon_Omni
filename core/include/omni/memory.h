#ifndef OMNI_MEMORY_H
#define OMNI_MEMORY_H
#include <stddef.h>
#if defined(__STDC_HOSTED__) && __STDC_HOSTED__
#include <string.h>
#else
/* Freestanding adapters supply these basic byte operations. */
void *memset(void *destination,int value,size_t length);
void *memcpy(void *destination,const void *source,size_t length);
int memcmp(const void *first,const void *second,size_t length);
#endif
#endif
