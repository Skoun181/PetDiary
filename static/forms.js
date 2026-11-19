"use strict";
const suggestionRoot=document.getElementById("pet-suggestions");
if(suggestionRoot){
  const breeds=JSON.parse(suggestionRoot.dataset.breeds);
  const species=document.getElementById("field-species");
  const list=document.getElementById("list-breed");
  const refresh=()=>{
    const key=Object.keys(breeds).find(k=>k.toLocaleLowerCase("de")===species.value.trim().toLocaleLowerCase("de"));
    list.replaceChildren(...(key?breeds[key]:[]).map(value=>{const o=document.createElement("option");o.value=value;return o;}));
  };
  species.addEventListener("input",refresh);
  refresh();
}
const med=document.getElementById("med-fields");
const kind=document.querySelector('select[name="kind"]');
if(med&&kind){
  const refresh=()=>{med.hidden=kind.value!=="med";};
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
