'use strict';
// Display translations are editorial labels; official identity citations do not certify translations.
const suffix={
 'Alola-Totem':'阿罗拉霸主','Alola':'阿罗拉','Galar':'伽勒尔','Hisui':'洗翠','Paldea':'帕底亚',
 'Belle':'贵妇装扮','Cosplay':'换装形态','Libre':'面罩摔角手','PhD':'博士装扮','Pop-Star':'偶像装扮','Rock-Star':'摇滚装扮','Starter':'搭档形态','Spiky-eared':'刺刺耳',
 'Paldea-Aqua':'帕底亚水澜种','Paldea-Blaze':'帕底亚火炽种','Paldea-Combat':'帕底亚斗战种',
 'Exclamation':'！','Question':'？','Sandy':'砂土蓑衣','Trash':'垃圾蓑衣','White-Striped':'白条纹','Autumn':'秋天','Summer':'夏天','Winter':'冬天',
 'Burn':'火焰卡带','Chill':'冰冻卡带','Douse':'水流卡带','Shock':'闪电卡带','Bond':'牵绊变身特性个体',
 'Archipelago':'群岛花纹','Continental':'大陆花纹','Elegant':'高雅花纹','Fancy':'花园花纹','Garden':'庭园花纹','High Plains':'荒野花纹','Icy Snow':'冰雪花纹','Jungle':'热带雨林花纹','Marine':'大海花纹','Modern':'摩登花纹','Monsoon':'骤雨花纹','Ocean':'大洋花纹','Pokeball':'球球花纹','Polar':'雪国花纹','River':'大河花纹','Sandstorm':'沙尘花纹','Savanna':'热带草原花纹','Sun':'太阳花纹','Tundra':'雪原花纹',
 'Blue':'蓝色','Orange':'橙色','White':'白色','Yellow':'黄色','Eternal':'永恒之花','Dandy':'绅士造型','Debutante':'淑女造型','Diamond':'菱形造型','Heart':'心形造型','Kabuki':'歌舞伎造型','La Reine':'女王造型','Matron':'贵妇造型','Pharaoh':'国王造型','Star':'星形造型',
 'F-Mega':'雌性超级进化','M-Mega':'雄性超级进化','Totem':'霸主','Dusk':'黄昏','Busted-Totem':'现形霸主','Original-Mega':'原始颜色超级进化','Antique':'真品',
 'Four':'四只家庭','Hero':'全能形态','Curly-Mega':'上弓姿势超级进化','Droopy-Mega':'下垂姿势超级进化','Stretchy-Mega':'平挺姿势超级进化','Droopy':'下垂姿势','Stretchy':'平挺姿势','Three-Segment':'三节形态','Roaming':'徒步形态',
 'Cornerstone-Tera':'础石面具太晶化','Hearthflame-Tera':'火灶面具太晶化','Teal-Tera':'碧草面具太晶化','Wellspring-Tera':'水井面具太晶化',
};
const creams={'vanilla-cream':'奶香香草','ruby-cream':'奶香红钻','matcha-cream':'奶香抹茶','mint-cream':'奶香薄荷','lemon-cream':'奶香柠檬','salted-cream':'奶香海盐','ruby-swirl':'红钻综合','caramel-swirl':'焦糖综合','rainbow-swirl':'三色综合'};
const sweets={strawberry:'草莓',berry:'野莓',love:'爱心',star:'星星',clover:'幸运草',flower:'花朵',ribbon:'蝴蝶结'};
const colors={red:'红色',orange:'橙色',yellow:'黄色',green:'绿色',blue:'蓝色',indigo:'靛蓝色',violet:'紫色'};
const modes={'limited-build':'收敛形态','sprinting-build':'疾驰形态','swimming-build':'浮水形态','gliding-build':'滑翔形态','low-power-mode':'低功率模式','drive-mode':'行驶模式','aquatic-mode':'浮游模式','glide-mode':'滑翔模式'};
function label(e,s,base,typeNames){
 const caps={Original:'初始',Hoenn:'丰缘',Sinnoh:'神奥',Unova:'合众',Kalos:'卡洛斯',Alola:'阿罗拉',Partner:'就决定是你了',World:'世界'};
 if(s?.baseSpecies==='Pikachu'&&caps[s.forme])return `${base} · ${caps[s.forme]}之帽`;
 if(s?.id==='darmanitangalarzen')return `${base} · 伽勒尔达摩模式`;
 const id=e.pokeapi?.identifier;
 if(id?.startsWith('alcremie-')&&id!=='alcremie-gmax'){
  const m=id.match(/^alcremie-(.+)-(strawberry|berry|love|star|clover|flower|ribbon)-sweet$/);
  if(m)return `${base} · ${creams[m[1]]}＋${sweets[m[2]]}糖饰`;
 }
 if(id?.startsWith('minior-')){const m=id.match(/^minior-(red|orange|yellow|green|blue|indigo|violet)(-meteor)?$/);if(m)return `${base} · ${colors[m[1]]}${m[2]?'流星形态':'核心'}`;}
 if(e.supplemental&&id){const mode=id.replace(/^(koraidon|miraidon)-/,'');if(modes[mode])return `${base} · ${modes[mode]}`;}
 if(e.category==='base')return e.name_zh_hans;
 if(['Arceus','Silvally'].includes(s?.baseSpecies)&&typeNames[s.forme])return `${base} · ${typeNames[s.forme]}属性`;
 if(s?.id==='rockruffdusk')return `${base} · 我行我素个体`;
 if(e.form_name_zh&&!['mega','gigantamax'].includes(e.category))return `${base} · ${e.form_name_zh}`;
 if(suffix[s?.forme])return `${base} · ${suffix[s.forme]}`;
 return e.name_zh_hans;
}
function category(e,s){
 if(e.category==='base'||e.category==='rocket_bond_candidate'||e.category==='dynamax'||['mega','gigantamax','regional','primal_reversion','ultra_burst','tera_related'].includes(e.category))return e.category;
 if(['Arceus','Silvally','Genesect'].includes(s?.baseSpecies))return 'type_form';
 if(['Kyurem','Necrozma','Calyrex'].includes(s?.baseSpecies))return 'fusion';
 if(s?.forme?.includes('Totem')||['Pumpkaboo','Gourgeist'].includes(s?.baseSpecies))return 'size_form';
 if(['Meowstic','Indeedee','Basculegion','Oinkologne','Frillish','Jellicent','Pyroar'].includes(s?.baseSpecies)&&!s.isMega)return 'gender_form';
 if(e.pokeapi?.battle_only||s?.battleOnly)return 'battle_state';
 if(['Pikachu','Pichu','Burmy','Deerling','Sawsbuck','Shellos','Gastrodon','Vivillon','Flabébé','Floette','Florges','Furfrou','Minior','Alcremie','Sinistea','Polteageist','Maushold','Dudunsparce','Poltchageist','Sinistcha','Tatsugiri','Squawkabilly','Unown','Xerneas'].includes(s?.baseSpecies)&&!['floetteeternal','pikachustarter'].includes(s?.id))return 'cosmetic';
 return e.category==='cosmetic'?'cosmetic':'special_form';
}
module.exports={label,category};
