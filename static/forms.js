"use strict";
// Progressive enhancement: keep the original inputs as canonical form values.
const normalize=value=>value.toLocaleLowerCase("de").normalize("NFD").replace(/[\u0300-\u036f]/g,"");
const controls=[];
const closeOthers=current=>controls.forEach(c=>{if(c!==current)c.close();});
function enhance(input,source,strict=false){
  const wrapper=document.createElement("div");
  wrapper.className="combo";
  input.before(wrapper);
  wrapper.append(input);
  const menu=document.createElement("div");
  menu.className="combo-menu";menu.id="combo-menu-"+controls.length;
  menu.setAttribute("role","listbox");menu.hidden=true;
  const toggle=document.createElement("button");
  toggle.type="button";toggle.className="combo-toggle";toggle.textContent="⌄";
  toggle.setAttribute("aria-label","Vorschläge anzeigen");toggle.tabIndex=-1;
  wrapper.append(toggle,menu);
  input.setAttribute("role","combobox");input.setAttribute("aria-autocomplete","list");
  input.setAttribute("aria-controls",menu.id);input.setAttribute("aria-expanded","false");
  input.setAttribute("autocomplete","off");
  let active=-1,items=[],committed=input.value;
  function close(){
    menu.hidden=true;input.setAttribute("aria-expanded","false");
    input.removeAttribute("aria-activedescendant");active=-1;
  }
  function choose(item){
    input.value=item.label;committed=item.label;
    if(strict){source.value=item.value;source.dispatchEvent(new Event("change",{bubbles:true}));}
    else {input.dispatchEvent(new Event("change",{bubbles:true}));input.dispatchEvent(new Event("input",{bubbles:true}));}
    close();input.focus();close();
  }
  function options(){
    return strict?Array.from(source.options).filter(o=>!o.disabled).map(o=>({label:o.textContent.trim(),value:o.value})):
      Array.from(source.options,o=>({label:o.value,value:o.value}));
  }
  function draw(all=false){
    closeOthers(control);
    const needle=all?"":normalize(input.value.trim());
    const matches=options().filter(o=>needle.split(/\s+/).every(t=>normalize(o.label).includes(t)));
    items=matches.slice(0,80);
    const value=input.value.trim();
    if(!strict&&value&&!options().some(o=>normalize(o.label)===normalize(value)))items.unshift({label:value,value,custom:true});
    menu.replaceChildren();active=-1;input.removeAttribute("aria-activedescendant");
    for(const [i,item] of items.entries()){
      const option=document.createElement("div");option.className="combo-option";option.id=menu.id+"-"+i;
      option.setAttribute("role","option");option.setAttribute("aria-selected","false");
      option.textContent=item.custom?"＋ Eigene Eingabe: "+item.label:item.label;
      option.addEventListener("pointerdown",e=>e.preventDefault());
      option.addEventListener("click",()=>choose(item));menu.append(option);
    }
    if(!items.length||matches.length>80){
      const info=document.createElement("div");info.className="combo-info";
      info.textContent=items.length?"Weitere Treffer: Suche eingrenzen.":strict?"Keine Treffer.":"Keine Vorschläge – eigene Eingabe möglich.";
      menu.append(info);
    }
    menu.hidden=false;input.setAttribute("aria-expanded","true");
  }
  function setActive(index){
    if(!items.length)return;
    active=(index+items.length)%items.length;
    const nodes=menu.querySelectorAll(".combo-option");
    nodes.forEach((n,i)=>n.setAttribute("aria-selected",String(i===active)));
    input.setAttribute("aria-activedescendant",nodes[active].id);
    nodes[active].scrollIntoView({block:"nearest"});
  }
  function restore(){
    if(strict)input.value=source.selectedOptions[0]?.textContent.trim()||committed;
    close();
  }
  const control={close:restore,refresh:()=>{if(!menu.hidden)draw();}};
  controls.push(control);
  input.addEventListener("focus",()=>draw(true));
  input.addEventListener("input",()=>draw());
  input.addEventListener("keydown",event=>{
    if(event.key==="ArrowDown"||event.key==="ArrowUp"){
      event.preventDefault();
      if(menu.hidden)draw(true);
      setActive(active<0?(event.key==="ArrowDown"?0:items.length-1):active+(event.key==="ArrowDown"?1:-1));
    }else if(event.key==="Enter"&&!menu.hidden){
      if(active>=0){event.preventDefault();choose(items[active]);}
      else if(strict){event.preventDefault();if(items.length===1)choose(items[0]);else restore();}
      else{event.preventDefault();close();}
    }else if(event.key==="Escape"){event.preventDefault();restore();}
    else if(event.key==="Tab")restore();
  });
  input.addEventListener("blur",()=>restore());
  toggle.addEventListener("pointerdown",event=>event.preventDefault());
  toggle.addEventListener("click",()=>{if(!menu.hidden)restore();else{input.focus();draw(true);}});
  document.addEventListener("pointerdown",event=>{if(!wrapper.contains(event.target))restore();});
  if(strict){
    source.addEventListener("change",()=>{input.value=source.selectedOptions[0]?.textContent.trim()||"";committed=input.value;});
  }
  return control;
}
const suggestionControls=new Map();
document.querySelectorAll("input[list]").forEach(input=>{
  const list=document.getElementById(input.getAttribute("list"));
  if(!list)return;
  input.removeAttribute("list");
  suggestionControls.set(input.id,enhance(input,list));
});
document.querySelectorAll("select").forEach(select=>{
  if(select.multiple||select.size>1)return;
  const input=document.createElement("input");
  input.type="text";input.value=select.selectedOptions[0]?.textContent.trim()||"";
  input.id=(select.id||"select-"+controls.length)+"-search";
  const label=select.closest("label");
  if(label)label.htmlFor=input.id;
  select.before(input);select.hidden=true;
  enhance(input,select,true);
});
const suggestionRoot=document.getElementById("pet-suggestions");
if(suggestionRoot){
  const breeds=JSON.parse(suggestionRoot.dataset.breeds);
  const species=document.getElementById("field-species");
  const list=document.getElementById("list-breed");
  const refresh=()=>{
    const key=Object.keys(breeds).find(k=>normalize(k)===normalize(species.value.trim()));
    list.replaceChildren(...(key?breeds[key]:[]).map(value=>{const o=document.createElement("option");o.value=value;return o;}));
    suggestionControls.get("field-breed")?.refresh();
  };
  species.addEventListener("input",refresh);
  refresh();
}
const med=document.getElementById("med-fields");
const kind=document.querySelector('select[name="kind"]');
if(med&&kind){
  const dateLabel=document.getElementById("record-date-label");
  const ordinary=document.getElementById("ordinary-reminder");
  const extra=document.getElementById("med-reminder");
  const content=document.getElementById("reminder-content");
  const help=document.getElementById("reminder-help");
  const refresh=()=>{
    const medication=kind.value==="med";
    med.hidden=!medication;
    if(dateLabel)dateLabel.textContent=medication?"Behandlungsbeginn *":kind.value==="vaccine"?"Impfdatum *":"Datum *";
    document.querySelectorAll("[data-record-kinds]").forEach(section=>{
      section.hidden=!section.dataset.recordKinds.split(" ").includes(kind.value)&&section.dataset.keep!=="yes";
    });
    if(content&&ordinary&&extra){
      ordinary.hidden=medication;extra.hidden=!medication;
      (medication?document.getElementById("med-reminder-placeholder"):document.getElementById("ordinary-reminder-placeholder")).append(content);
      help.textContent=medication?"Nur für einen zusätzlichen Termin, etwa eine Nachkontrolle. Die Einnahmeerinnerungen entstehen aus dem Medikamentenplan.":"Bei Impfungen wird ohne separates Erinnerungsdatum das Gültigkeitsende übernommen. Bei zukünftigen Terminen das Termindatum.";
    }
  };
  kind.addEventListener("change",refresh);
  refresh();
  const add=document.getElementById("add-clock");
  add.addEventListener("click",()=>{
    const next=med.querySelector(".clock-field[hidden]");
    if(next){next.hidden=false;next.querySelector("input").focus();}
    if(!med.querySelector(".clock-field[hidden]"))add.hidden=true;
  });
  if(!med.querySelector(".clock-field[hidden]"))add.hidden=true;
}
