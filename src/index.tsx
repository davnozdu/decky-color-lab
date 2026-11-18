import {ButtonItem, DropdownItem, PanelSection, PanelSectionRow, SliderField, ToggleField, staticClasses} from "@decky/ui";
import {callable, definePlugin, toaster} from "@decky/api";
import {useEffect, useRef, useState} from "react";
import {FaPalette} from "react-icons/fa";

interface State {
 enabled:boolean;auto:boolean;preset:string;kind:string;tracking:boolean;strength:number;black:number;
 display:{name:string;internal:boolean};application:{name:string;key:string};busy:boolean;waiting:boolean;last_error:string;
 last_analysis:number|null;analysis_ms:number|null;analysis_cpu_ms:number|null;capture_ms:number|null;cycle_ms:number|null;cycle_cpu_ms:number|null;interval:number;interval_effective:number;battery_w:number|null;model:string;model_id:string;capture:string;engine:string;hdr_npu_available:boolean;
}
const getState=callable<[],State>("get_state");
const configure=callable<[changes:Record<string,unknown>],State>("configure");
const analyze=callable<[force:boolean],State>("analyze");
const presets=[{data:"cinema",label:"Кино"},{data:"game",label:"Игры"},{data:"soft",label:"Мягкий"},
 {data:"black",label:"Глубокий чёрный"},{data:"hdr",label:"Псевдо-HDR · SDR"}];

function Content(){
 const [state,setState]=useState<State|null>(null);
 const pending=useRef(false);const timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const notify=(error:unknown)=>toaster.toast({title:"Color Lab",body:String(error)});
 useEffect(()=>{
  let mounted=true;
  const refresh=()=>getState().then(s=>{if(mounted&&!pending.current)setState(s);}).catch(notify);
  refresh();const id=setInterval(refresh,2500);
  return()=>{mounted=false;clearInterval(id);if(timer.current)clearTimeout(timer.current);};
 },[]);
 const update=async(changes:Record<string,unknown>)=>{
  pending.current=true;
  try{setState(await configure(changes));}catch(error){notify(error);}finally{pending.current=false;}
 };
 const slider=(key:"strength"|"black",value:number)=>{
  setState(s=>s?{...s,[key]:value}:s);pending.current=true;
  if(timer.current)clearTimeout(timer.current);
  timer.current=setTimeout(()=>{void update({[key]:value});},180);
 };
 if(!state)return <PanelSection><PanelSectionRow>Загрузка профиля…</PanelSectionRow></PanelSection>;
 return <>
  <PanelSection title={state.display.internal?"Встроенный экран":"Внешний экран"}>
   <PanelSectionRow><div style={{fontSize:12,opacity:.7}}>{state.display.name} · {state.application.name}</div></PanelSectionRow>
   {state.application.key!=="steam"&&<PanelSectionRow><DropdownItem label="Тип приложения" description="Видео: «Кино», псевдо-HDR и мгновенная подстройка при смене сцены. Игра: игровая предустановка." rgOptions={[{data:"game",label:"Игра"},{data:"video",label:"Фильмы и видео"}]} selectedOption={state.kind} onChange={v=>void update({kind:v.data})}/></PanelSectionRow>}
   <PanelSectionRow><ToggleField label="Цветокоррекция" checked={state.enabled} onChange={v=>void update({enabled:v})}/></PanelSectionRow>
   <PanelSectionRow><DropdownItem label="Предустановка" rgOptions={presets} selectedOption={state.preset} onChange={v=>void update({preset:v.data})}/></PanelSectionRow>
   <PanelSectionRow><SliderField label="Сила обработки" value={state.strength} min={0} max={100} step={5} showValue valueSuffix="%" onChange={v=>slider("strength",v)}/></PanelSectionRow>
   <PanelSectionRow><SliderField label="Глубина чёрного" value={state.black} min={0} max={30} step={2} showValue valueSuffix="%" onChange={v=>slider("black",v)}/></PanelSectionRow>
   <PanelSectionRow><ButtonItem layout="below" onClick={()=>void update({enabled:!state.enabled})}>{state.enabled?"Сравнить: выключить":"Сравнить: включить"}</ButtonItem></PanelSectionRow>
  </PanelSection>
  <PanelSection title="Нейросетевая адаптация">
   <PanelSectionRow><DropdownItem label="Модель" rgOptions={[{data:"adaptive",label:"Адаптивный цвет · 3DLUT"},{data:"hdr",label:"SDR → HDR → SDR · HDRTVNet++"}]} selectedOption={state.model_id} onChange={v=>void update({model_id:v.data})}/></PanelSectionRow>
   <PanelSectionRow><DropdownItem label="Исполнитель" rgOptions={[{data:"cpu",label:"CPU · эталон"},...((state.model_id!=="hdr"||state.hdr_npu_available)?[{data:"npu",label:"CPU + NPU · эксперимент"}]:[])]} selectedOption={state.engine} onChange={v=>void update({engine:v.data})}/></PanelSectionRow>
   <PanelSectionRow><div style={{fontSize:12,opacity:.8}}>{state.model}</div></PanelSectionRow>
   <PanelSectionRow><ToggleField label="Автоанализ сцены" description={state.interval?`Не чаще одного раза в ${state.interval} с; коэффициенты усредняются.`:`Авто: сейчас раз в ${state.interval_effective} с (1–10 с по динамике картинки).`} checked={state.auto} onChange={v=>void update({auto:v})}/></PanelSectionRow>
   <PanelSectionRow><ToggleField label="Мгновенно при смене сцены" description="Лёгкая проверка кадра 2 раза в секунду на CPU; нейросеть запускается сразу при смене сцены." disabled={!state.auto} checked={state.tracking} onChange={v=>void update({tracking:v})}/></PanelSectionRow>
   <PanelSectionRow><DropdownItem label="Интервал анализа" rgOptions={[{data:0,label:"Авто (по динамике сцены)"},...[1,2,5,10,15,30,60].map(n=>({data:n,label:`Раз в ${n} с`}))]} selectedOption={state.interval} onChange={v=>void update({interval:v.data})}/></PanelSectionRow>
   <PanelSectionRow><ButtonItem layout="below" disabled={state.busy||!state.enabled} onClick={async()=>{pending.current=true;try{setState(await analyze(true));}catch(e){notify(e);}finally{pending.current=false;}}}>{state.busy?"Анализ сцены…":"Проанализировать сейчас"}</ButtonItem></PanelSectionRow>
   <PanelSectionRow><div style={{fontSize:12,opacity:.7}}>{state.last_analysis?`Последний анализ: ${new Date(state.last_analysis*1000).toLocaleTimeString()}`:"Применена подготовленная цветовая таблица"}{state.analysis_ms!=null?` · ${state.analysis_ms.toFixed(1)} мс${state.analysis_cpu_ms!=null?` (CPU: ${state.analysis_cpu_ms.toFixed(1)} мс)`:""}`:""}</div></PanelSectionRow>
   {state.cycle_ms!=null&&<PanelSectionRow><div style={{fontSize:12,opacity:.7}}>Полный фоновый цикл: {(state.cycle_ms/1000).toFixed(2)} с.{state.cycle_cpu_ms!=null?` CPU плагина ≈ ${state.cycle_cpu_ms.toFixed(1)} мс`:""}. Это не время кадра.</div></PanelSectionRow>}
   {state.waiting&&<PanelSectionRow><div style={{fontSize:12,opacity:.7}}>Ожидание нового кадра приложения…</div></PanelSectionRow>}
   {state.last_error&&<PanelSectionRow><div style={{fontSize:12,color:"#f0b45e"}}>{state.last_error}</div></PanelSectionRow>}
  </PanelSection>
  <PanelSection title="Состояние">
   <PanelSectionRow><div style={{fontSize:12,opacity:.7}}>Обе модели выводят SDR. HDRTVNet++: глобальная нейросетевая HDR-реконструкция с тональным преобразованием в SDR; без локального восстановления деталей. Захват PipeWire без скриншотов. Профиль сохраняется для текущего приложения и экрана.{state.battery_w!=null?` Батарея: ${state.battery_w.toFixed(1)} Вт (вся приставка).`:""}</div></PanelSectionRow>
  </PanelSection>
 </>;
}
export default definePlugin(()=>({name:"Decky Color Lab",titleView:<div className={staticClasses.Title}>Color Lab</div>,content:<Content/>,icon:<FaPalette/>,onDismount(){}}));
