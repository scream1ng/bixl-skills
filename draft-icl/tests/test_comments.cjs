// Execute the real comment controller against a small DOM harness; no browser dependency.
const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
class Element{
  constructor(tag='div'){this.tag=tag;this.children=[];this.dataset={};this.style={};this.attrs={};this.textContent='';this.hidden=false;this.events={};this.bounds={left:0,top:0,right:100,width:100,height:40};this.classes=new Set();this.classList={add:x=>this.classes.add(x),remove:x=>this.classes.delete(x),toggle:(x,on)=>{const use=on??!this.classes.has(x);if(use)this.classes.add(x);else this.classes.delete(x);return use;}};}
  set className(v){this.classes=new Set(v.split(' '));}get className(){return [...this.classes].join(' ');}
  append(...kids){for(const child of kids){child.parent=this;this.children.push(child);}}
  replaceChildren(...kids){this.children=[];this.append(...kids);}
  setAttribute(k,v){this.attrs[k]=v;}getAttribute(k){return this.attrs[k];}
  addEventListener(k,fn){this.events[k]=fn;}
  getBoundingClientRect(){return this.bounds;}
  focus(){this.focused=true;}select(){this.selected=true;}
  closest(q){let e=this;while(e){if(q==='[data-check]'&&e.dataset.check)return e;if(q[0]==='#'&&e.id===q.slice(1))return e;e=e.parent;}return null;}
}
const saved=new Map();let failStorage=false,clipboardWorks=false,copied;
function environment(){
  const ids={};for(const id of ['drawing','pins','logo','notes','status','mode','copy','exported']){ids[id]=new Element();ids[id].id=id;}
  const sheet=new Element();sheet.bounds={left:20,top:100,right:1520,width:1500,height:1000};sheet.append(ids.pins,ids.drawing);
  ids.drawing.bounds={left:40,top:700,right:1040,width:1000,height:500};ids.logo.attrs.src='image';
  const row=new Element('tr');row.dataset.check='height';const cell=new Element('td');cell.bounds={left:40,top:200,right:90,width:50,height:40};row.append(cell);sheet.append(row);
  const document={body:new Element(),getElementById:id=>ids[id],querySelector:()=>sheet,querySelectorAll:()=>[row],createElement:tag=>new Element(tag)};
  const meta={process:'bending',name:'Main Body',number:'TBC',revision:3,fingerprint:'digest123',check_labels:{height:'B1'}};
  const context=vm.createContext({meta,document,localStorage:{getItem:k=>saved.get(k),setItem:(k,v)=>{if(failStorage)throw Error('blocked');saved.set(k,v);}},navigator:{clipboard:{writeText:async value=>{if(!clipboardWorks)throw Error('blocked');copied=value;}}},addEventListener(){},URL,Blob,setTimeout});
  vm.runInContext(fs.readFileSync(path.join(__dirname,'../scripts/comments.js'),'utf8'),context);
  return {context,ids,row,sheet,run:s=>vm.runInContext(s,context)};
}
(async()=>{
  let e=environment();e.ids.mode.onclick();assert.equal(e.ids.mode.attrs['aria-pressed'],'true');
  e.sheet.events.click({target:e.ids.drawing,clientX:540,clientY:950});
  assert.equal(e.ids.pins.children.length,1);let pin=e.ids.pins.children[0],box=pin.children[1],area=box.children[1];
  assert(!pin.classes.has('shut'));assert.equal(pin.children[0].children[0].textContent,'C1');assert.equal(area.focused,true);
  area.value='Move this label <script>bad</script>';area.oninput();assert(e.ids.notes.textContent.includes('C1. Move this label'));assert(e.ids.notes.textContent.includes('[0.5, 0.5] (normalized)'));
  pin.children[0].onclick({stopPropagation(){}});assert(pin.classes.has('shut'));pin.children[0].onclick({stopPropagation(){}});assert(!pin.classes.has('shut'));
  e.row.events.keydown({key:'Enter',target:e.row,preventDefault(){}});assert.equal(e.ids.pins.children.length,2);
  let second=e.ids.pins.children[1];second.children[1].children[1].value='Check this flange';second.children[1].children[1].oninput();assert(e.ids.notes.textContent.includes('C2. Check this flange on B1'));
  e.ids.pins.children[0].children[1].children[2].onclick({stopPropagation(){}});assert.equal(e.ids.pins.children.length,1);assert.equal(e.ids.pins.children[0].children[0].children[0].textContent,'C1');
  await e.ids.copy.onclick();assert.equal(e.ids.exported.hidden,false);assert.equal(e.ids.exported.selected,true);assert(e.ids.exported.value.includes('BENDING ICL — Main Body — revision 3'));assert(e.ids.exported.value.includes('C1. Check this flange on B1'));assert(!e.ids.exported.value.startsWith('{'));
  clipboardWorks=true;await e.ids.copy.onclick();assert(e.ids.exported.hidden);assert(copied.includes('C1. Check this flange'));
  e=environment();assert.equal(e.ids.pins.children.length,1);assert.equal(e.run('comments[0].text'),'Check this flange');assert(e.ids.pins.children[0].classes.has('shut'));
  failStorage=true;area=e.ids.pins.children[0].children[1].children[1];area.value='Still editable offline';area.oninput();assert(e.ids.status.textContent.includes('Local storage unavailable'));assert(e.ids.notes.textContent.includes('Still editable offline'));
  const key='design-icl:bending:digest123';saved.set(key,JSON.stringify([{check:'wrong',text:'bad'},{check:null,text:'bad',position:{x:2,y:0}},{check:null,text:'valid',position:{x:.2,y:.3}}]));
  e=environment();assert.equal(e.run('comments.length'),1);assert.equal(e.run('comments[0].text'),'valid');
  console.log('Comment controller checks passed: pins, editing, collapse/reopen, row keyboard, deletion/renumbering, copy fallback, persistence and invalid saved notes.');
})().catch(error=>{console.error(error);process.exitCode=1;});
