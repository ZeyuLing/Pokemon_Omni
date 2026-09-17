#include "omni/pokedex.h"

static int shape(const OmniDex *d) { return d && d->entries && d->count; }
static int state_ok(const OmniDex *d,const OmniDexState *s) { return shape(d) && s && s->flags && s->count==d->count; }
static int flags_ok(uint8_t f) { return !(f & 248u) && (!(f&2u)||(f&1u)) && (!(f&4u)||((f&3u)==3u)); }
static uint8_t lower(uint8_t c) { return c>='A'&&c<='Z'?(uint8_t)(c+32):c; }
static int contains(const char *s,const char *q) {
    size_t i,j;
    if(!q||!*q) return 1;
    if(!s) return 0;
    for(i=0;s[i];++i) {
        for(j=0;q[j]&&s[i+j]&&lower((uint8_t)s[i+j])==lower((uint8_t)q[j]);++j) {}
        if(!q[j]) return 1;
    }
    return 0;
}
int omni_dex_validate(const OmniDex *d) {
    uint16_t i,j;
    if(!shape(d)) return OMNI_DEX_ARGUMENT;
    for(i=0;i<d->count;++i) {
        const OmniDexEntry *e=&d->entries[i];
        if(!e->id||!e->name_en||!e->name_zh||e->generation>9||e->research_only>1||e->category>31||e->type_mask_hi>3) return OMNI_DEX_ARGUMENT;
        for(j=0;j<i;++j) if(d->entries[j].id==e->id) return OMNI_DEX_DUPLICATE;
    }
    return OMNI_DEX_OK;
}
int32_t omni_dex_find(const OmniDex *d,uint32_t id) {
    uint16_t i;
    if(!shape(d)) return -1;
    for(i=0;i<d->count;++i) if(d->entries[i].id==id) return i;
    return -1;
}
int omni_dex_matches(const OmniDexEntry *e,uint8_t flags,const OmniDexFilter *f) {
    uint32_t mask;
    if(!e||!f||f->type>18||f->progress>4||f->include_research>1) return 0;
    if((e->research_only&&!f->include_research)||(f->national&&e->national!=f->national)
       ||(f->category&&e->category!=f->category)||(f->generation&&e->generation!=f->generation)) return 0;
    mask=(uint32_t)e->type_mask|((uint32_t)e->type_mask_hi<<16);
    if(f->type&&!(mask&(UINT32_C(1)<<(f->type-1)))) return 0;
    if(f->progress==1&&flags) return 0; /* undiscovered */
    if(f->progress>1&&!(flags&(1u<<(f->progress-2)))) return 0;
    return contains(e->name_zh,f->text)||contains(e->name_en,f->text);
}
uint16_t omni_dex_query(const OmniDex *d,const OmniDexState *s,const OmniDexFilter *f,
    uint16_t offset,uint16_t *out,uint16_t capacity) {
    uint16_t i,total=0,written=0;
    if(!state_ok(d,s)||!f||(capacity&&!out)) return 0;
    for(i=0;i<d->count;++i) if(omni_dex_matches(&d->entries[i],s->flags[i],f)) {
        if(total>=offset&&written<capacity) out[written++]=i;
        ++total;
    }
    return total;
}
int omni_dex_record(const OmniDex *d,OmniDexState *s,uint32_t id,uint8_t event) {
    int32_t i;
    if(!state_ok(d,s)||(event!=1&&event!=2&&event!=4)) return OMNI_DEX_ARGUMENT;
    i=omni_dex_find(d,id);
    if(i<0) return OMNI_DEX_UNKNOWN;
    if(d->entries[i].research_only) return OMNI_DEX_RESEARCH;
    /* Caller supplies trusted gameplay events; this is not an anti-cheat boundary. */
    s->flags[i]|=event==4?7:event==2?3:1;
    return OMNI_DEX_OK;
}
uint16_t omni_dex_count(const OmniDex *d,const OmniDexState *s,uint8_t flag,uint8_t research) {
    uint16_t i,n=0;
    if(!state_ok(d,s)||research>1||(flag!=0&&flag!=1&&flag!=2&&flag!=4)) return 0;
    for(i=0;i<d->count;++i) if((research||!d->entries[i].research_only)&&(!flag||(s->flags[i]&flag))) ++n;
    return n;
}
static void put32(uint8_t *p,uint32_t n) { uint8_t i; for(i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24); }
static uint32_t hash(const uint8_t *p,size_t n) { uint32_t h=UINT32_C(2166136261);size_t i;for(i=0;i<n;++i)h=(h^p[i])*UINT32_C(16777619);return h; }
size_t omni_dex_save_size(const OmniDexState *s) {
    size_t n=0;uint16_t i;
    if(!s||!s->flags)return 0;
    for(i=0;i<s->count;++i) if(s->flags[i])++n;
    return 16+n*5;
}
int omni_dex_save(const OmniDex *d,const OmniDexState *s,uint8_t *out,size_t cap,size_t *written) {
    uint16_t i;size_t pos=12,size;
    if(!state_ok(d,s)||!out||!written)return OMNI_DEX_ARGUMENT;
    for(i=0;i<s->count;++i) if(!flags_ok(s->flags[i])||(d->entries[i].research_only&&s->flags[i]))return OMNI_DEX_ARGUMENT;
    size=omni_dex_save_size(s);if(cap<size)return OMNI_DEX_CAPACITY;
    out[0]='O';out[1]='D';out[2]='E';out[3]='X';put32(out+4,1);put32(out+8,(uint32_t)((size-16)/5));
    for(i=0;i<s->count;++i)if(s->flags[i]) { put32(out+pos,d->entries[i].id);out[pos+4]=s->flags[i];pos+=5; }
    put32(out+pos,hash(out,pos));*written=size;return OMNI_DEX_OK;
}
int omni_dex_load(const OmniDex *d,OmniDexState *s,const uint8_t *in,size_t length) {
    uint32_t count,i,j;int32_t index;
    if(!state_ok(d,s)||!in)return OMNI_DEX_ARGUMENT;
    if(length<16||in[0]!='O'||in[1]!='D'||in[2]!='E'||in[3]!='X'||get32(in+4)!=1)return OMNI_DEX_BAD_SAVE;
    count=get32(in+8);
    if(count>65535u||length!=16+(size_t)count*5||get32(in+length-4)!=hash(in,length-4))return OMNI_DEX_BAD_SAVE;
    for(i=0;i<count;++i) {
        const uint8_t *p=in+12+i*5;uint32_t id=get32(p);
        if(!id||!p[4]||!flags_ok(p[4]))return OMNI_DEX_BAD_SAVE;
        for(j=0;j<i;++j)if(get32(in+12+j*5)==id)return OMNI_DEX_DUPLICATE;
    }
    for(i=0;i<s->count;++i)s->flags[i]=0;
    for(i=0;i<count;++i) {
        index=omni_dex_find(d,get32(in+12+i*5));
        if(index>=0&&!d->entries[index].research_only)s->flags[index]=in[16+i*5];
    }
    return OMNI_DEX_OK;
}
