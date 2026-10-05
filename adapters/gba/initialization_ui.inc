/* GBA staging and controls. Story text and rewards are portable data/core. */
static void gary_walk(unsigned leaving){
 unsigned i;gary_path_count=0;gary_leaving=(uint8_t)leaving;gary_present=gary_moving=1;
 for(i=12;i>=5;--i)gary_path[gary_path_count++]=(OmniWalkPoint){96,(int16_t)((i+1)*16)};
 gary_path[gary_path_count++]=(OmniWalkPoint){80,96};gary_path[gary_path_count++]=(OmniWalkPoint){80,80};
 if(leaving)for(i=0;i<gary_path_count/2;++i){OmniWalkPoint t=gary_path[i];gary_path[i]=gary_path[gary_path_count-1-i];gary_path[gary_path_count-1-i]=t;}
 gary_x=gary_path[0].x;gary_y=gary_path[0].y-16;gary_direction=leaving?0:1;gary_clock=omni_gba_clock();screen=STORY_MOVE;dirty=1;
}
static void story_move_tick(void){
 const PalletMap *m=map();OmniWalkGrid grid={pallet_world_blob+m->collision,m->w,m->h};OmniWalkPoint point;uint8_t face=1;
 unsigned ticks=(uint16_t)(omni_gba_clock()-gary_clock),duration=(gary_path_count-1)*8;
 if(!omni_walk_sample(&grid,gary_path,gary_path_count,ticks,duration,&point,&face)){gary_moving=0;message("人物路线被阻挡，请与博士重新交谈。",AFTER_WORLD);return;}
 gary_x=point.x;gary_y=point.y-16;gary_direction=face;
 if(ticks>=duration){gary_moving=0;if(gary_leaving)gary_present=0;story_next();}
}
static void initialization_fight(unsigned kind){
 if(omni_initialization_battle(&game,&battle,(uint8_t)kind,&omni_pokedex_catalog,&dex_state)){story_seq=255;message("伙伴还需要休息。请准备好再来。",AFTER_WORLD);return;}
 if(kind==OMNI_BATTLE_TUTORIAL){battle.mons[1].hp=1;tutorial_bag_seen=0;}
 story_seq=255;menu_cursor=battle_page=battle_cursor=0;screen=BATTLE;dirty=1;
}
static void story_next(void){
 while(story_seq!=255&&story_beat<omni_story_ranges[story_seq][1]){
  const OmniStoryBeat *b=&omni_story_beats[omni_story_ranges[story_seq][0]+story_beat++];
  if(*b->text){message(b->text,AFTER_STORY);return;}
  switch(b->action){
  case STORY_ACTION_WAKE_DONE:game.events|=OMNI_EVENT_WOKE;save_game();break;
  case STORY_ACTION_GIFTS:
   if(omni_initialization_gifts(&game,&omni_pokedex_catalog,&dex_state)){story_seq=255;message("这份出发礼物已经领取。",AFTER_WORLD);return;}
   save_game();message("搭档皮卡丘与关都御三家加入队伍！\n获得图鉴、100个精灵球与培养工具包。",AFTER_STORY);return;
  case STORY_ACTION_GARY_ENTER:gary_walk(0);return;
  case STORY_ACTION_GARY_LEAVE:gary_walk(1);return;
  case STORY_ACTION_GARY_BATTLE:initialization_fight(OMNI_BATTLE_GARY);return;
  case STORY_ACTION_OLD_CHOICE:story_seq=255;menu_cursor=0;screen=OLD_CHOICE;dirty=1;return;
  case STORY_ACTION_OLD_TUTORIAL:initialization_fight(OMNI_BATTLE_TUTORIAL);return;
  case STORY_ACTION_OLD_BATTLE:initialization_fight(OMNI_BATTLE_OLD_MAN);return;
  case STORY_ACTION_WEEDLE:{unsigned boxed=game.party_count>=6;int r=omni_initialization_weedle(&game,&omni_pokedex_catalog,&dex_state);save_game();message(r?"队伍和电脑都满了。老人会替你保管，\n整理电脑后再来领取。":boxed?"收到了独角虫！\n队伍已满，独角虫送入了电脑。":"收到了独角虫！\n独角虫加入了队伍。",AFTER_STORY);return;}
  default:break;
  }
 }
 story_seq=255;screen=WORLD;dirty=1;save_game();
}
static void story_start(unsigned id){riding=0;omni_travel_reset(&travel,game.location,travel_species(),px*16,py*16);story_seq=(uint8_t)id;story_beat=0;story_next();}
static void initialization_resume(void){
 gary_present=0;story_seq=255;
 if(!(game.events&OMNI_EVENT_INITIALIZATION))return;
 if(!(game.events&OMNI_EVENT_WOKE)&&game.location==OMNI_BEDROOM)story_start(STORY_WAKE);
 else if((game.events&OMNI_EVENT_GIFTS)&&!(game.events&OMNI_EVENT_GARY_DONE)&&game.location==OMNI_LAB)story_start(STORY_GARY_RETURN);
}
static void initialization_result(unsigned kind,unsigned outcome){
 save_game();encounter_cooldown=6;
 if(kind==OMNI_BATTLE_GARY){gary_present=1;gary_x=80;gary_y=64;story_start(outcome==1?STORY_GARY_WIN:STORY_GARY_LOSS);}
 else story_start(kind==OMNI_BATTLE_TUTORIAL?STORY_OLD_CAUGHT:outcome==1?STORY_OLD_WIN:STORY_OLD_LOSS);
}
static const char *training_names[]={"性格薄荷","特性胶囊","一键6V","努力值调整器","穿洞绳"};
static const char *stat_names[]={"HP","攻击","防御","特攻","特防","速度"};
static void draw_training(void){
 const OmniPartner *m=&game.party[party_cursor];unsigned i,total=0;
 box(0,0,240,160,PAPER);panel(0,0,240,160);text(10,7,training_names[training_tool],BLUE,232);
 text(10,29,omni_partner_name(m),INK,166);text(168,29,"Lv",MUTED,190);num(191,29,m->level,INK);
 if(training_tool==OMNI_TOOL_EV){
  for(i=0;i<6;++i){int x=12+(int)(i%2)*116,y=52+(int)(i/2)*22;text(x,y,stat_names[i],INK,x+55);num(x+58,y,m->evs[i],BLUE);if(i==training_field)menu_arrow(x-7,y+3,INK);total+=m->evs[i];}
  text(10,121,"合计",MUTED,62);num(62,121,total,INK);text(89,121,"/510",MUTED,136);
  text(10,142,"方向调整 A最大 SELECT清零",INK,234);
 }else{
  if(training_tool==OMNI_TOOL_MINT){text(12,61,"当前",MUTED,65);text(76,61,omni_nature_name(m->nature),INK,225);text(12,85,"选择",MUTED,65);text(76,85,omni_nature_name(training_value),BLUE,225);text(12,110,"上下选择性格，A使用薄荷。",INK,232);}
  if(training_tool==OMNI_TOOL_ABILITY){text(12,62,"当前特性",MUTED,113);text(115,62,omni_partner_ability(m),INK,232);text(12,92,"A切换合法的普通特性。",INK,232);text(12,111,"只有一个普通特性时不会改变。",MUTED,232);}
  if(training_tool==OMNI_TOOL_IV){for(i=0;i<6;++i){int x=12+(int)(i%3)*75,y=62+(int)(i/3)*26;text(x,y,stat_names[i],MUTED,x+53);num(x+45,y,m->ivs[i],INK);}text(12,116,"A将六项个体值设为31。",INK,232);}
  text(12,141,"L/R选伙伴 B返回 不消耗",BLUE,232);
 }
}
static void training_tick(uint16_t pressed){
 int result=0,apply=0;OmniPartner *m;
 if(pressed&B){screen=BAG;return;}
 if(pressed&L)party_cursor=(party_cursor+game.party_count-1)%game.party_count;
 if(pressed&R)party_cursor=(party_cursor+1)%game.party_count;
 m=&game.party[party_cursor];
 if(training_tool==OMNI_TOOL_MINT){if(pressed&UP)training_value=(training_value+24)%25;if(pressed&DOWN)training_value=(training_value+1)%25;if(pressed&A){result=omni_adventure_train(&game,party_cursor,training_tool,0,training_value);apply=1;}}
 else if(training_tool==OMNI_TOOL_EV){unsigned value=m->evs[training_field];if(pressed&UP)training_field=(training_field+5)%6;if(pressed&DOWN)training_field=(training_field+1)%6;
  if(pressed&LEFT){value=value>3?value-4:0;apply=1;}if(pressed&RIGHT){value=value<249?value+4:252;apply=1;}if(pressed&SELECT){value=0;apply=1;}
  if(pressed&A){unsigned i,other=0;for(i=0;i<6;++i)if(i!=training_field)other+=m->evs[i];value=510-other;if(value>252)value=252;apply=1;}
  if(apply)result=omni_adventure_train(&game,party_cursor,training_tool,training_field,(uint16_t)value);
 }else if(pressed&A){result=omni_adventure_train(&game,party_cursor,training_tool,0,0);apply=1;}
 if(apply){if(result)message(result==OMNI_ADVENTURE_ALREADY?"这只伙伴只有一个普通特性。\n胶囊不会改变它，也不会消耗。":"努力值单项最多252，合计最多510。\n请先降低其他项目。",AFTER_TRAINING);else{save_game();if(training_tool!=OMNI_TOOL_EV)message("培养设置已更新并保存。\n工具可以继续使用。",AFTER_TRAINING);}}
}
static void draw_storage(void){
 unsigned i,count=storage_mode?game.party_count:game.storage_count;box(0,0,240,160,PAPER);panel(0,0,240,160);text(12,8,storage_mode?"电脑：寄存伙伴":"电脑：领取伙伴",BLUE,232);
 if(!count)text(12,57,"电脑里还没有伙伴。",INK,232);
 for(i=0;i<count;++i){const OmniPartner *m=storage_mode?&game.party[i]:&game.storage[i];int x=15+(int)(i%2)*113,y=33+(int)(i/2)*17;text(x,y,omni_partner_name(m),INK,x+104);if(i==storage_cursor)menu_arrow(x-8,y+3,INK);}
 text(12,142,"SELECT切换 A确认 B返回",BLUE,232);
}
static void storage_tick(uint16_t pressed){
 unsigned count=storage_mode?game.party_count:game.storage_count;if(pressed&B){screen=WORLD;return;}if(pressed&SELECT){storage_mode^=1;storage_cursor=0;return;}
 if(!count)return;if(pressed&UP)storage_cursor=(storage_cursor+count-1)%count;if(pressed&DOWN)storage_cursor=(storage_cursor+1)%count;
 if(pressed&A){int r=storage_mode?omni_adventure_store(&game,storage_cursor):omni_adventure_withdraw(&game,storage_cursor);if(r)message("队伍至少保留一只伙伴，最多六只。\n电脑最多存放十二只。",AFTER_STORAGE);else{storage_cursor=0;save_game();}}
}
