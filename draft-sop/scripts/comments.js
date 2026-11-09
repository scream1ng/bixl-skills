const $=id=>document.getElementById(id),storageKey='draft-sop:'+meta.part+':'+meta.fingerprint;
const sheet=document.querySelector('.sheet');
let comments=[],active=false;
try{const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');
  if(Array.isArray(saved))comments=saved.filter(c=>c&&typeof c.text==='string'&&Object.hasOwn(meta.steps,c.step)&&
    (!c.position||['x','y'].every(k=>Number.isFinite(c.position[k])&&c.position[k]>=0&&c.position[k]<=1)));}catch(e){}
function say(v){$('status').textContent=v;$('status').hidden=!v;}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(comments));}catch(e){say('Local storage unavailable. Copy comments before closing.');}}
function stepEl(key){return Array.from(document.querySelectorAll('.step')).find(s=>s.dataset.step===key);}
function target(c){return `Step ${meta.steps[c.step]} (${c.step}) ${c.position?'photo':'text'}`;}
function report(){
  $('notes').textContent=comments.map((c,i)=>`C${i+1}. ${c.text||'(empty)'} — ${target(c)}${c.position?' @ ['+[c.position.x,c.position.y].map(v=>v.toFixed(3)).join(', ')+']':''}`).join('\n');
  $('notes').hidden=!comments.length;
}
function placePins(){
  const b=sheet.getBoundingClientRect();
  for(const pin of Array.from($('pins').children)){
    const c=comments[Number(pin.dataset.index)],el=c&&stepEl(c.step);if(!el){pin.hidden=true;continue;}
    let x,y;
    if(c.position){const r=el.querySelector('.photo').getBoundingClientRect();x=r.left-b.left+c.position.x*r.width;y=r.top-b.top+c.position.y*r.height;}
    else{const r=el.querySelector('.text').getBoundingClientRect();x=r.right-b.left-8;y=r.top-b.top+r.height/2;}
    pin.hidden=false;pin.style.left=x+'px';pin.style.top=y+'px';
    pin.classList.toggle('flip',x>b.width-240);pin.classList.toggle('below',y<110);
  }
}
function render(focus=null){
  $('pins').replaceChildren();
  comments.forEach((c,i)=>{
    const pin=document.createElement('div');pin.className='pin shut';pin.dataset.index=i;
    const marker=document.createElement('button');marker.className='marker';marker.type='button';marker.setAttribute('aria-label','Edit comment C'+(i+1));
    const label=document.createElement('span');label.textContent='C'+(i+1);marker.append(label);
    const box=document.createElement('div');box.className='box';
    const cap=document.createElement('strong');cap.className='target';cap.textContent=target(c);
    const area=document.createElement('textarea');area.placeholder='What should change here?';area.value=c.text;
    const del=document.createElement('button');del.className='del';del.type='button';del.textContent='Delete';
    marker.onclick=e=>{e.stopPropagation();if(!pin.classList.toggle('shut'))area.focus();};
    area.oninput=()=>{c.text=area.value;persist();report();};
    area.onkeydown=e=>{if(e.key==='Escape'){pin.classList.add('shut');marker.focus();}};
    del.onclick=e=>{e.stopPropagation();comments.splice(i,1);persist();render();};
    box.append(cap,area,del);pin.append(marker,box);$('pins').append(pin);
    if(i===focus){pin.classList.remove('shut');area.focus();}
  });
  report();placePins();
}
$('mode').onclick=()=>{active=!active;$('mode').setAttribute('aria-pressed',String(active));document.body.classList.toggle('commenting',active);say(active?'Click a photo or step text to comment.':'');};
sheet.addEventListener('click',e=>{
  if(!active||e.target.closest('#pins'))return;
  const step=e.target.closest('.step'),photo=e.target.closest('.photo'),text=e.target.closest('.text');
  if(!step||(!photo&&!text))return;
  const c={step:step.dataset.step,text:''};
  if(photo){const r=photo.getBoundingClientRect();c.position={x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height))};}
  comments.push(c);persist();render(comments.length-1);
});
function readable(){return `SOP ${meta.part} — ${meta.name} — revision ${meta.revision}\nSpec: ${meta.fingerprint}\n\n${$('notes').textContent}`;}
$('copy').onclick=async()=>{
  if(!comments.length){say('No comments yet.');return;}
  const v=readable(),buf=$('exported');buf.value=v;buf.hidden=false;buf.focus();buf.select();say('Press ⌘C / Ctrl+C to copy.');
  try{await navigator.clipboard.writeText(v);buf.hidden=true;say('Copied.');}catch(e){}
};
addEventListener('resize',placePins);
if(typeof ResizeObserver!=='undefined')new ResizeObserver(placePins).observe(sheet);
render();
