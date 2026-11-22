"use strict";
(function(){
  const root=document.documentElement;
  const valid=["system","light","dark"];
  let choice="system";
  try { const saved=localStorage.getItem("petdiary-theme"); if(valid.includes(saved)) choice=saved; } catch(e) {}
  const media=window.matchMedia("(prefers-color-scheme: dark)");
  function apply(){root.dataset.theme=choice==="system"?(media.matches?"dark":"light"):choice;}
  apply();
  media.addEventListener("change",apply);
  document.addEventListener("DOMContentLoaded",()=>{
    const select=document.getElementById("theme-choice");
    if(!select)return;
    select.value=choice;
    select.addEventListener("change",()=>{
      if(!valid.includes(select.value))return;
      choice=select.value;
      try{localStorage.setItem("petdiary-theme",choice);}catch(e){}
      apply();
    });
  });
})();
