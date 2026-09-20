/* Public release metadata only. Never downloads or commits a ROM or save. */
const fs=require('node:fs');
const videos=['BV1F9eq6hEHK','BV1QKe16vEsp','BV1FHen6EEoy','BV1Rye46dEyy'];
async function get(url){const r=await fetch(url,{signal:AbortSignal.timeout(20000)});if(!r.ok)throw Error(`HTTP ${r.status}`);const j=await r.json();if(j.code!==0)throw Error(`API ${j.code}: ${j.message}`);return j.data;}
(async()=>{
 const sources=[];
 for(const bvid of videos){
  const v=await get(`https://api.bilibili.com/x/web-interface/view?bvid=${bvid}`);
  const comments=await get(`https://api.bilibili.com/x/v2/reply?type=1&oid=${v.aid}&sort=2&pn=1`);
  const top=comments.upper?.top;
  sources.push({url:`https://www.bilibili.com/video/${bvid}/`,bvid,aid:v.aid,publisher:v.owner.name,publisher_id:v.owner.mid,published_at:new Date(v.pubdate*1000).toISOString(),title:v.title,
   pinned_by_publisher:top?.mid===v.owner.mid?{comment_id:top.rpid,text:top.content.message}:null});
 }
 const report={checked_on:new Date().toISOString().slice(0,10),method:'Unauthenticated Bilibili public view and reply APIs; pinned comment owner IDs checked against video owner IDs.',
  branch_policy:'Community continuation / subsequent modification; no assertion that this is the original Ultra Emerald team release.',sources,
  download_candidates:[{url:'https://pan.quark.cn/s/fcb4317bef30',source_video:'BV1Rye46dEyy',source_comment_id:317912136832,kind:'Third-party modification / sharing edition',label:'5.8 神战最终版；视频注明永久超进化、补全进化石及内置便利功能',status:'Link confirmed in publisher pinned comment. Share file listing and ROM contents not verified; no download or hash yet.'}],
  form_leads:[{names:['黑暗超梦','超级烈焰猴'],source:'https://jingxuan.douyin.com/m/video/7682735816355439002',evidence:'5.8.2 video title visible in the publisher related-video list. Target page timed out.',status:'Names only; sprites, stats, abilities, learnsets and evolution rules unverified.'},{source:'https://jingxuan.douyin.com/m/video/7683503599255558490',evidence:'5.8.4 update title claims ZA Mega coverage and permanent Mega.',status:'Publisher claim, not a verified roster.'},{source:'https://jingxuan.douyin.com/m/video/7684211176858880074',evidence:'5.8.6 update title claims six additional Mega forms.',status:'Exact six names and data unverified.'}],
  next_steps:['Obtain exact ROM/patch and hash, then identify base branch and changes.','Extract sprites, base stats, types, abilities, learnsets and form conditions into source-scoped reference records.','Map to existing identities; same artwork or nickname alone is insufficient identity evidence.','Only approve Omni battle data after cross-checking values and rules.'],
  limitations:['Bilibili pages and Quark share could not be inspected with the web reader; browser research pages timed out.','Public API verifies titles, publishers and pinned URLs, not the files behind a share link.','No additional 5.8 form imported or declared complete during this research.']};
 fs.writeFileSync('research/ultra-emerald-5.8-sources.json',JSON.stringify(report,null,2)+'\n');
 console.log(`Recorded ${sources.length} release sources and one attributed download candidate; ROM unverified.`);
})().catch(e=>{console.error(e);process.exitCode=1;});
