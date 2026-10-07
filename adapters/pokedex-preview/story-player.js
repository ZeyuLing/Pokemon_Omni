'use strict';
const video=document.querySelector('#story-video'),nav=document.querySelector('#chapters'),status=document.querySelector('#duration');
const time=seconds=>`${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
fetch('/story-playthrough.json').then(r=>{if(!r.ok)throw Error('missing');return r.json();}).then(meta=>{
 status.textContent=`全长 ${time(meta.seconds)} · 连续实机录像，含游戏音乐与音效`;
 const buttons=meta.chapters.map(chapter=>{const button=document.createElement('button');button.type='button';button.textContent=`${time(chapter.seconds)} ${chapter.title}`;button.addEventListener('click',()=>{video.currentTime=chapter.seconds;video.play().catch(()=>{});});nav.append(button);return button;});
 video.addEventListener('timeupdate',()=>{let active=-1;meta.chapters.forEach((c,i)=>{if(video.currentTime>=c.seconds)active=i;});buttons.forEach((b,i)=>b.setAttribute('aria-current',String(i===active)));});
}).catch(()=>{status.textContent='完整录像尚未生成。请先运行剧情录制与编码工具。';});
