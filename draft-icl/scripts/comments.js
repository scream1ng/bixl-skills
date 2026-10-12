const $=id=>document.getElementById(id),storageKey='design-icl:'+meta.process+':'+meta.fingerprint;
const sheet=document.querySelector('.sheet'),drawing=$('drawing');
let comments=[],active=false;
try {
  const saved=JSON.parse(localStorage.getItem(storageKey)||'[]');
  if(Array.isArray(saved)) comments=saved.filter(c=>c&&typeof c.text==='string'&&
    (c.check===null||Object.hasOwn(meta.check_labels,c.check))&&
    (!c.position||(['x','y'].every(k=>Number.isFinite(c.position[k])&&c.position[k]>=0&&c.position[k]<=1))));
} catch(e) {}
if(!$('logo').getAttribute('src')) $('logo').hidden=true;
function say(value){$('status').textContent=value;$('status').hidden=!value;}
function persist(){try{localStorage.setItem(storageKey,JSON.stringify(comments));}catch(e){say('Local storage unavailable. Copy comments before closing.');}}
function target(c){return meta.check_labels[c.check]||'Drawing';}
function report(){
  $('notes').textContent=comments.length?comments.map((c,i)=>`C${i+1}. ${c.text||'(empty)'} on ${target(c)}${c.position?' @ drawing ['+['x','y'].map(k=>Number(c.position[k].toFixed(5))).join(', ')+'] (normalized)':''}`).join('\n'):'';
  $('notes').hidden=!comments.length;
}
function rowFor(key){return Array.from(document.querySelectorAll('tr[data-check]')).find(r=>r.dataset.check===key);}
function placePins(){
  const bounds=sheet.getBoundingClientRect(),db=drawing.getBoundingClientRect();
  for(const pin of Array.from($('pins').children)){
    const c=comments[Number(pin.dataset.index)];if(!c)continue;
    let x,y;
    if(c.position){x=db.left-bounds.left+c.position.x*db.width;y=db.top-bounds.top+c.position.y*db.height;}
    else{const row=rowFor(c.check);if(!row){pin.hidden=true;continue;}const cell=row.children[0].getBoundingClientRect();x=cell.right-bounds.left-5;y=cell.top-bounds.top+cell.height/2;}
    pin.hidden=false;pin.style.left=(x+(sheet.scrollLeft||0))+'px';pin.style.top=(y+(sheet.scrollTop||0))+'px';
    pin.classList.toggle('flip',x>bounds.width-235);pin.classList.toggle('below',y<110);
  }
}
function render(focusIndex=null){
  $('pins').replaceChildren();
  comments.forEach((c,i)=>{
    const pin=document.createElement('div');pin.className='pin shut';pin.dataset.index=i;
    const marker=document.createElement('button');marker.className='marker';marker.type='button';marker.setAttribute('aria-label','Edit comment C'+(i+1));marker.setAttribute('aria-expanded','false');
    const label=document.createElement('span');label.textContent='C'+(i+1);marker.append(label);
    const box=document.createElement('div');box.className='box';
    const caption=document.createElement('strong');caption.className='target';caption.textContent=target(c);
    const area=document.createElement('textarea');area.placeholder='What should change here?';area.setAttribute('aria-label','Comment C'+(i+1));area.value=c.text;
    const del=document.createElement('button');del.className='del';del.type='button';del.textContent='Delete';del.setAttribute('aria-label','Delete comment C'+(i+1));
    marker.onclick=e=>{e.stopPropagation();const closed=pin.classList.toggle('shut');marker.setAttribute('aria-expanded',String(!closed));if(!closed)area.focus();};
    area.oninput=()=>{c.text=area.value;persist();report();};
    area.onkeydown=e=>{if(e.key==='Escape'){pin.classList.add('shut');marker.setAttribute('aria-expanded','false');marker.focus();}};
    del.onclick=e=>{e.stopPropagation();comments.splice(i,1);persist();render();};
    box.append(caption,area,del);pin.append(marker,box);$('pins').append(pin);
    if(i===focusIndex){pin.classList.remove('shut');marker.setAttribute('aria-expanded','true');area.focus();}
  });
  report();placePins();
}
$('mode').onclick=()=>{active=!active;$('mode').setAttribute('aria-pressed',String(active));document.body.classList.toggle('commenting',active);say(active?'Click to add a comment.':'');};
function select(event){
  if(!active||event.target.closest('#pins'))return;
  const hit=event.target.closest('[data-check]'),inDrawing=event.target.closest('#drawing');
  if(!hit&&!inDrawing)return;
  const c={check:hit?.dataset.check||null,text:''};
  if(inDrawing){const box=drawing.getBoundingClientRect();c.position={x:Math.max(0,Math.min(1,(event.clientX-box.left)/box.width)),y:Math.max(0,Math.min(1,(event.clientY-box.top)/box.height))};}
  comments.push(c);persist();render(comments.length-1);
}
sheet.addEventListener('click',select);
document.querySelectorAll('tr[data-check]').forEach(row=>row.addEventListener('keydown',e=>{if(active&&(e.key==='Enter'||e.key===' ')){e.preventDefault();select(e);}}));
function payload(){return JSON.stringify({process:meta.process,part:meta.number,revision:meta.revision,fingerprint:meta.fingerprint,comments},null,2);}
function readable(){return `${meta.process.toUpperCase()} ICL — ${meta.name} — revision ${meta.revision}\nSpec: ${meta.fingerprint}\n\n${$('notes').textContent}`;}
$('copy').onclick=async()=>{
  if(!comments.length){say('No comments yet.');return;}
  const value=readable(),buffer=$('exported');buffer.value=value;buffer.hidden=false;buffer.focus();buffer.select();say('Press ⌘C / Ctrl+C to copy.');
  try{await navigator.clipboard.writeText(value);buffer.hidden=true;say('Copied.');}catch(e){}
};
addEventListener('resize',placePins);sheet.addEventListener('scroll',placePins);
if(typeof ResizeObserver!=='undefined')new ResizeObserver(placePins).observe(sheet);
render();
