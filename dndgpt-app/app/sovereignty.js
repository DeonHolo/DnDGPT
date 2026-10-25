let currentGame=window.openai?.toolOutput?.game_id||window.openai?.widgetState?.game_id||"age-of-convergence",gameEpoch=0,gameSwitching=false,gameLocked=false;
let sovereignTab="domain";
function isSovereignFoundation(a){return a.scope==="sovereign"&&["domain","general","army"].includes(a.sovereign_role)&&String(a.activation).toLowerCase()==="passive"&&!["parent_id","parent_ability_id","parent_skill_id"].some(k=>a[k])}
function visibleSovereignOperation(next,op){return op.known!==false&&(next.sovereignty.commanders.find(c=>c.id===op.commander_id)?.side!=="enemy"||op.known===true)}
const gameNames={"age-of-convergence":"Age of Convergence","sovereign-system":"Sovereign System"};
const gameSelections={};
function sovereignCombatView(next){
  const allies=new Map((next.summons||[]).map(c=>[c.id,c]));
  if(next.game_id==="sovereign-system")for(const c of next.sovereignty?.commanders||[])if(c.side!=="enemy")allies.set(c.id,c);
  return {...next,summons:[...allies.values()]};
}
let lastGameContext="";
function selectedGameContext(){return {game_id:currentGame,campaign_id:state?.id||null,selection_only:true,rules_request:state?{campaign_id:state.id}:{game_id:currentGame}}}
function publishGameContext(){
  const context=selectedGameContext(),key=JSON.stringify(context);if(key===lastGameContext)return;lastGameContext=key;
  if(standard)rpc("ui/update-model-context",{structuredContent:context}).catch(()=>{});
  try{window.openai?.setWidgetState?.({...window.openai.widgetState,game_id:currentGame,campaign_id:state?.id||null,modelContent:context,view_preferences:preferences})}catch{}
}
const sovereignNav=element("button");sovereignNav.id="nav-sovereignty";sovereignNav.className="section-link";sovereignNav.type="button";sovereignNav.dataset.target="sovereignty";sovereignNav.setAttribute("aria-controls","page-sovereignty");sovereignNav.hidden=true;
const sovereignCopy=element("span",undefined,"nav-copy");sovereignCopy.append(element("span","Sovereignty","nav-title"));const sovereignPreview=element("span","Domain, commanders and forces","panel-preview");sovereignPreview.id="sovereigntyPreview";sovereignCopy.append(sovereignPreview);sovereignNav.append(sovereignCopy);$("sectionNav").insertBefore(sovereignNav,$("nav-gallery"));sovereignNav.onclick=()=>selectCompanionPage("sovereignty");
const crown=document.createElementNS("http://www.w3.org/2000/svg","svg");crown.setAttribute("viewBox","0 0 24 24");crown.setAttribute("class","nav-icon");crown.setAttribute("fill","none");crown.setAttribute("stroke","currentColor");crown.setAttribute("stroke-width","1.5");crown.setAttribute("aria-hidden","true");const crownPath=document.createElementNS(crown.namespaceURI,"path");crownPath.setAttribute("d","M3 7l5 4 4-7 4 7 5-4-2 12H5L3 7ZM5 16h14");crown.append(crownPath);sovereignNav.prepend(crown);sovereignNav.append(element("span","08","nav-index"));
sovereignNav.onkeydown=event=>{if(!["ArrowRight","ArrowDown","ArrowLeft","ArrowUp","Home","End"].includes(event.key))return;event.preventDefault();const controls=[...document.querySelectorAll('#sectionNav [data-target]')].filter(b=>!b.hidden),index=controls.indexOf(sovereignNav),next=event.key==="Home"?0:event.key==="End"?controls.length-1:(index+(["ArrowRight","ArrowDown"].includes(event.key)?1:-1)+controls.length)%controls.length;controls[next].focus();controls[next].click()};

function activateGame(id){
  if(!gameNames[id])return;
  const changed=currentGame!==id;currentGame=id;
  document.documentElement.dataset.game=id;$("gameSelect").value=id;
  document.querySelector(".identity h1").textContent=id==="sovereign-system"?"Sovereign System":"DnDGPT";
  sovereignNav.hidden=id!=="sovereign-system";
  $("nav-gallery").querySelector(".nav-index").textContent=id==="sovereign-system"?"09":"08";
  if(changed){campaigns=[];$("session").replaceChildren(element("option","Select a saved game"));$("session").firstElementChild.value="";if(id!=="sovereign-system"&&document.querySelector('#sectionNav [aria-current="page"]')===sovereignNav)selectCompanionPage("character")}
}
function clearGameSnapshot(){
  resetDashboardSearch();
  if(state)gameSelections[currentGame]=state.id;
  state=null;lastSelected=null;lastVerifiedAt=null;syncIssue=false;pending=null;dismissedProposal=null;
  galleryReset(null);$("approval").hidden=true;$("resources").replaceChildren();$("hero").textContent="No campaign selected";$("progress").textContent="Select a saved game to continue.";$("location").textContent="";$("xpMeter").value=0;$("stateVersion").textContent="No saved state selected";$("lastEvent").textContent="";
  if(!deletionStarted){deletion=null;if($("deleteDialog").open)$("deleteDialog").close()}
  for(const id of ["character","skills","health","summons","equipment","quests","world","sovereignty"]){$(id).replaceChildren();paragraph($(id),"Select a saved game to view this chapter.","muted");if($(id+"Preview"))$(id+"Preview").textContent="No state selected"}
  renderChoices();updateSyncStatus();updateSaveTools();
}
async function switchGame(id){
  if(!gameNames[id]||id===currentGame||deleting||deletionStarted||busy)return;
  gameLocked=true;gameEpoch++;clearTimeout(savingTimer);clearGameSnapshot();activateGame(id);gameSwitching=true;
  publishGameContext();
  try{
    await callTool("render_dashboard",{game_id:id});
    const previous=gameSelections[id];
    if(previous&&campaigns.some(c=>c.id===previous))await callTool("get_campaign",{campaign_id:previous});
    notice(campaigns.length?"Showing "+gameNames[id]+" saves.":"No "+gameNames[id]+" campaigns yet. Start one when ready.");
    publishGameContext();
  }catch(error){notice(error.message)}finally{gameSwitching=false}
}
function entityPowers(parent,entity){
  for(const ability of entity.abilities||[]){
    const disclosure=element("details");disclosure.append(element("summary",ability.name||"Recorded power"));
    const reader=element("article",undefined,"ability-inspector");disclosure.append(reader);parent.append(disclosure);
    renderAbilityInspector(reader,{...ability,id:entity.id+":"+ability.id});
  }
}
function renderStartingSovereignKit(next){
  if(next.game_id!=="sovereign-system"||next.phase!=="character_draft")return;
  const root=element("section",undefined,"starting-sovereign-kit");root.append(element("h3","Your sovereignty","group"));
  paragraph(root,"Your domain, general and army grow through permanent Sovereign Evolutions.");
  const inspect=element("button","Inspect Sovereignty");inspect.type="button";inspect.onclick=()=>selectCompanionPage("sovereignty");root.append(inspect);
  const missing=next.rules_check?.sovereign_kit?.missing_roles||[];
  if(missing.length)paragraph(root,"Still taking shape: "+missing.map(fieldLabel).join(", ")+".","muted");
  $("character").append(root);
}
function renderFoundation(parent,next,role){
  const powers=(next.abilities||[]).filter(a=>isSovereignFoundation(a)&&a.sovereign_role===role);
  if(!powers.length)return;
  const section=element("section",undefined,"sovereign-foundation");section.append(element("h3","Sovereign upgrades","group"));
  entityPowers(section,{id:"foundation-"+role,abilities:powers});parent.append(section);
}
function sovereigntyCard(parent,title,meta,description){
  const card=element("section",undefined,"sovereign-card");card.append(element("h3",title));if(meta)paragraph(card,meta,"sovereign-meta");if(description)paragraph(card,description);parent.append(card);return card;
}
function renderSovereignty(next){
  const root=$("sovereignty");root.replaceChildren();
  if((next.game_id||"age-of-convergence")!=="sovereign-system")return;
  const s=next.sovereignty;if(!s){paragraph(root,"Your domain has not been established yet.","muted");return}
  const ownCommanders=s.commanders.filter(c=>c.side!=="enemy").length,ownFormations=s.formations.filter(f=>f.side==="player").length;
  $("sovereigntyPreview").textContent="Domain "+s.domain.level+" · "+ownCommanders+(ownCommanders===1?" commander":" commanders")+" · "+ownFormations+(ownFormations===1?" formation":" formations");
  const tabs=element("div",undefined,"sovereign-tabs");tabs.setAttribute("role","tablist");tabs.setAttribute("aria-label","Sovereignty records");root.append(tabs);
  const panels={};
  for(const [id,label]of [["domain","Domain"],["commanders","Commanders"],["forces","Forces"],["operations","Operations & fronts"]]){
    const button=element("button",label);button.type="button";button.id="sovereign-tab-"+id;button.setAttribute("role","tab");button.setAttribute("aria-controls","sovereign-panel-"+id);
    const panel=element("div");panel.id="sovereign-panel-"+id;panel.setAttribute("role","tabpanel");panel.setAttribute("aria-labelledby",button.id);panels[id]=panel;
    const select=()=>{sovereignTab=id;for(const b of tabs.children){const on=b===button;b.setAttribute("aria-selected",String(on));b.tabIndex=on?0:-1}for(const [key,node]of Object.entries(panels))node.hidden=key!==id};button.onclick=select;tabs.append(button);root.append(panel);
    button.onkeydown=event=>{if(!["ArrowRight","ArrowLeft","Home","End"].includes(event.key))return;event.preventDefault();const controls=[...tabs.children],index=controls.indexOf(button);const target=event.key==="Home"?0:event.key==="End"?controls.length-1:(index+(event.key==="ArrowRight"?1:-1)+controls.length)%controls.length;controls[target].click();controls[target].focus()};
  }
  const domain=sovereigntyCard(panels.domain,s.domain.name,"Domain level "+s.domain.level,s.domain.description);
  for(const capability of s.domain.capabilities||[]){domain.append(element("h4",capability.name||"Domain capability"));paragraph(domain,capability.description||capability.mechanics_display||"")}
  if(s.domain.limits)paragraph(domain,"Force capacity · "+s.formations.filter(f=>f.side==="player"&&f.status!=="destroyed").reduce((sum,f)=>sum+f.strength,0)+" / "+s.domain.limits.max_strength+" strength · "+s.domain.limits.max_formations+" formations","sovereign-meta");
  const credit=Math.max(0,s.ascension_earned-s.ascension_spent.length);if(credit)paragraph(domain,"Sovereign Evolutions available · "+credit,"pending");
  const milestone=s.domain.next_milestone;
  if(milestone){
    const section=sovereigntyCard(panels.domain,milestone.title,"Next domain level · "+milestone.target_level);
    const done=milestone.objectives.filter(o=>o.status==="done").length;const progress=element("progress");progress.max=milestone.objectives.length;progress.value=done;progress.setAttribute("aria-label","Domain milestone progress");section.append(progress);
    paragraph(section,done+" / "+milestone.objectives.length+" objectives complete","sovereign-meta");
    const list=element("ul",undefined,"sovereign-objectives");for(const o of milestone.objectives){const item=element("li",(o.status==="done"?"✓ ":"○ ")+o.text);if(o.status==="done")item.className="done";list.append(item)}section.append(list);
    const options=element("div",undefined,"development-options");
    for(const choice of milestone.choices){const button=element("button");button.type="button";button.disabled=done!==milestone.objectives.length;button.append(element("strong",choice.name),element("span",choice.description));button.onclick=()=>sendPrompt("Choose domain development "+choice.id+" ("+choice.name+") for milestone "+milestone.id+". Apply the published development and save it; no further approval.");options.append(button)}section.append(options);
  }
  if(s.developments.length){const history=recordDetail(panels.domain,"Completed developments","sovereign-developments");for(const d of s.developments)paragraph(history,"Level "+d.level+" · "+d.choice.name)}
  renderFoundation(panels.domain,next,"domain");renderFoundation(panels.commanders,next,"general");renderFoundation(panels.forces,next,"army");
  for(const c of s.commanders.filter(c=>c.side!=="enemy"||c.known===true)){const card=sovereigntyCard(panels.commanders,c.name,"Level "+c.level+" · XP "+(c.xp||0)+" / "+(100+50*(c.level-1))+" · "+(c.status||"active"),c.description);if(c.nature)paragraph(card,c.nature);entityPowers(card,c);if(c.equipment?.length){const gear=recordDetail(card,"Equipment","commander-gear-"+c.id);for(const item of c.equipment)renderValue(gear,item)}}
  if(!s.commanders.length)paragraph(panels.commanders,"Your first commander will appear here during creation.","muted");
  for(const f of s.formations.filter(f=>f.side==="player"||f.known===true)){const card=sovereigntyCard(panels.forces,f.name,(f.side==="player"?"Your forces":"Known opposing force")+" · "+f.strength+" / "+f.maximum_strength+" · "+(f.status||"active"),f.description);paragraph(card,"Veterancy "+(f.veterancy||0)+" / 5 · XP "+(f.xp_total||0)+" · Cohesion "+f.morale,"sovereign-meta");const commander=s.commanders.find(c=>c.id===f.commander_id);if(commander)paragraph(card,"Commander · "+commander.name);const stats=recordDetail(card,"Formation rules","formation-"+f.id);renderFacts(stats,[["Attack",f.attack],["Defense",f.defense],["Power",f.power],["Armor",f.armor]]);entityPowers(card,f)}
  for(const op of s.operations.filter(op=>visibleSovereignOperation(next,op))){const card=sovereigntyCard(panels.operations,op.name,op.status+" · "+(op.status==="active"?(next.fictional_time_seconds>=op.due_at?"Report due":"Orders underway"):"Report recorded"),op.objective);paragraph(card,op.mandate);if(op.outcome)paragraph(card,op.outcome)}
  for(const front of s.fronts.filter(f=>f.known!==false)){const card=sovereigntyCard(panels.operations,front.name,front.status||"active",front.objective);card.classList.add("sovereign-front");paragraph(card,"Your objective "+(front.player_progress||0)+" / "+front.target_progress);}
  if(s.battle_reports.length){const reports=recordDetail(panels.operations,"Battle reports","sovereign-battles");for(const r of s.battle_reports.slice(-10).reverse()){const front=s.fronts.find(f=>f.id===r.front_id);paragraph(reports,(front?.name||"Battle")+" · "+r.phases.length+" phases · "+r.outcome.replaceAll("_"," "));}}
  if(!s.operations.length&&!s.fronts.length)paragraph(panels.operations,"Standing orders and battle fronts appear here when established.","muted");
  $("sovereign-tab-"+sovereignTab).click();
}
$("gameSelect").onchange=()=>switchGame($("gameSelect").value);
$("newGame").onclick=()=>sendPrompt("Create a NEW "+gameNames[currentGame]+" campaign with game_id="+currentGame+". Read this game's rules and begin its World Preview and normal creation choices. Preserve existing campaigns.");
activateGame(currentGame);
