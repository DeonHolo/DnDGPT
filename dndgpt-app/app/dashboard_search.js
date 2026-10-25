/* Search only the selected campaign's player-facing records; no transport calls. */
let dashboardSearchEntries=[],dashboardSearchCampaign=null,dashboardSearchLimit=40;
const searchWords=value=>String(value||"").toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
const searchMatches=(value,words)=>words.every(word=>value.toLocaleLowerCase().includes(word));
function searchableText(node){
  const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT),parts=[];let current;
  while(current=walker.nextNode())if(!current.parentElement?.closest("script,style,[data-search-ignore]"))parts.push(current.textContent);
  return parts.join(" ").replace(/\s+/g," ").trim();
}
function searchPublicText(value){
  if(value?.known_to_player===false)return "";
  const clean=(item,depth=0)=>{
    if(depth>12||item?.known_to_player===false)return;
    if(Array.isArray(item))return item.map(child=>clean(child,depth+1)).filter(child=>child!==undefined);
    if(item&&typeof item==="object")return Object.fromEntries(Object.entries(item).filter(([key])=>publicField(key)&&!/^(?:gm|internal|hidden)(?:_|$)/i.test(key)).map(([key,child])=>[key,clean(child,depth+1)]));
    return item;
  };
  const holder=element("div");renderValue(holder,clean(value));return searchableText(holder);
}
function searchPowerText(ability,child){
  if(child)return [child.name,child.rarity,child.flavor_text,searchPublicText(upgradeContent(child,ability))].filter(Boolean).join(" ");
  return [ability.name,ability.rarity,activationLabel(ability),ability.flavor_text,
    ...[ability.simple||ability.description,ability.mechanics_display??ability.mechanics??ability.effect??ability.effects??ability.rules,
      ability.target,ability.damage,ability.duration,ability.prerequisites,ability.stacking,ability.manifestation??ability.visual]
      .map(value=>searchPublicText(abilityCopy(value)))].filter(Boolean).join(" ");
}
function searchLogKey(row,index){return row?.id||itemDetailKey("search-log",row&&typeof row==="object"?row:{text:row},index)}
function clearDashboardSearch(){
  $("dashboardSearch").value="";$("dashboardSearchResults").hidden=true;$("dashboardSearchList").replaceChildren();
  for(const node of document.querySelectorAll("[data-search-highlight]"))node.removeAttribute("data-search-highlight");
}
function resetDashboardSearch(){
  clearDashboardSearch();dashboardSearchEntries=[];dashboardSearchCampaign=null;
  $("dashboardSearch").disabled=true;$("dashboardSearchClear").disabled=true;$("dashboardSearchHint").textContent="Select a saved campaign to search.";
}
function refreshDashboardSearch(){
  if(!state||state.game_id&&state.game_id!==currentGame){resetDashboardSearch();return}
  if(dashboardSearchCampaign!==state.id)clearDashboardSearch();dashboardSearchCampaign=state.id;
  $("dashboardSearch").disabled=false;$("dashboardSearchClear").disabled=false;
  $("dashboardSearchHint").textContent="Search saved dashboard text in this campaign. Results open the matching entry.";
  const entries=[],add=(title,section,body,open)=>{if(title&&body)entries.push({title,section,body,text:[title,section,body].join(" "),open})};
  for(const id of ["character","skills","health","summons","equipment","quests","world","sovereignty","gallery"]){
    const nav=$("nav-"+id),root=$(id);if(!nav||nav.hidden||!root)continue;
    const title=nav.querySelector(".nav-label")?.textContent||$("title-"+id)?.textContent||fieldLabel(id);
    add(title,"Panel",id==="character"||id==="health"?searchableText(root):title,()=>{selectCompanionPage(id);return root});
  }
  for(const ability of state.abilities||[]){
    if(ability.known_to_player===false)continue;
    const foundation=isSovereignFoundation(ability)&&currentGame==="sovereign-system";
    const section=foundation?"Sovereignty":("Skills · "+skillTabs[skillGroup(ability)][1]);
    add(ability.name,section,searchPowerText(ability),()=>openSearchPower(ability,"rules"));
    for(const key of ["evolutions","imprints","integrated_imprints","upgrades"]){
      const children=Array.isArray(ability[key])?ability[key]:ability[key]?[ability[key]]:[];
      for(const child of children)if(child&&typeof child==="object"&&child.known_to_player!==false)
        add(child.name||"Upgrade",section+" › "+ability.name+" › Upgrades",searchPowerText(ability,child),()=>openSearchPower(ability,"upgrades",child));
    }
  }
  const domGroups=[
    ["#equipment .item-card","Equipment & inventory","equipment"],
    ["#quests .quest-card","Quest Journal","quests"],
    ["#world-page-living .life-card","People & places","world"],
    ["#sovereignty .sovereign-card","Sovereignty","sovereignty"],
    ["#galleryGrid .gallery-card","Gallery","gallery"]
  ];
  const actors=sovereignCombatView(state);
  for(const [group,enemy]of [[actors.summons,false],[actors.enemies,true]])for(const actor of group)
    add(actor.name,"Allies & combat",[actorSummary(actor),searchPublicText(actor)].join(" "),()=>openSearchActor(actor,enemy));
  for(const [selector,section,page]of domGroups)for(const node of document.querySelectorAll(selector)){
    const title=node.querySelector(".item-name,h3,summary")?.textContent;if(!title)continue;
    add(title,section,searchableText(node),()=>{selectCompanionPage(page);return node});
  }
  for(const [key,value]of Object.entries(state.world||{})){
    if(!publicField(key)||/^(?:gm|internal|hidden)(?:_|$)/i.test(key)||["title","name"].includes(key)||value?.known_to_player===false)continue;
    const body=searchPublicText(value);if(!body)continue;
    add(fieldLabel(key),"World",body,()=>{selectCompanionPage("world");selectWorldTab("world");const button=[...document.querySelectorAll("[data-world-article]")].find(b=>b.dataset.worldArticle===key);button?.click();return $("world-page-world").querySelector(".reading-article")});
  }
  const logs=[...(state.world_log||[])].filter(row=>row?.known_to_player!==false).reverse();
  if(state.notes)logs.unshift({name:"Current scene",text:state.notes});
  if(state.opening_preview&&state.phase!=="adventure")logs.push({name:"Opening preview",text:state.opening_preview});
  logs.forEach((row,index)=>{
    const body=typeof row==="string"?row:searchPublicText(row),title=row?.name||row?.title||briefText(row?.summary||row?.text||row,90);
    add(title||"Campaign entry","Campaign Log",body,()=>{selectCompanionPage("world");selectWorldTab("log");return $("world-page-log").revealSearchEntry?.(searchLogKey(row,index))});
  });
  dashboardSearchEntries=entries;drawDashboardSearch();
}
function openSearchPower(ability,view,child){
  let identity=ability.id;
  if(currentGame==="sovereign-system"&&isSovereignFoundation(ability)){
    selectCompanionPage("sovereignty");$("sovereign-tab-"+({domain:"domain",general:"commanders",army:"forces"}[ability.sovereign_role]))?.click();
    return sovereignSearchTargets.get(ability.id+":"+(child?.id||view));
  }else{
    selectCompanionPage("skills");const tab=skillTabs[skillGroup(ability)][0];selectSkillTab(tab);
    [...document.querySelectorAll("#skill-page-"+tab+" [data-ability-id]")].find(b=>b.dataset.abilityId===ability.id)?.click();
  }
  const suffix=String(identity||"ability").replace(/[^a-z0-9_-]/gi,"-");
  const button=$("ability-view-"+view+"-"+suffix);for(let node=button;node;node=node.parentElement)if(node.tagName==="DETAILS")node.open=true;
  button?.click();return $("ability-copy-"+view+"-"+suffix)||button;
}
function revealSearchResult(entry,words){
  $("hud").hidden=false;$("hideHud").textContent="Hide codex";
  let target=entry.open();if(!target)return;
  const walker=document.createTreeWalker(target,NodeFilter.SHOW_TEXT);let current;
  while(current=walker.nextNode())if(words.some(word=>current.textContent.toLocaleLowerCase().includes(word))){target=current.parentElement;break}
  const ancestors=[];for(let node=target;node;node=node.parentElement)ancestors.unshift(node);
  for(const node of ancestors){
    if(node.tagName==="DETAILS")node.open=true;
    if(node.getAttribute("role")==="tabpanel"&&node.id){const tab=[...document.querySelectorAll('[role="tab"][aria-controls]')].find(b=>b.getAttribute("aria-controls")===node.id);tab?.click()}
  }
  for(const node of document.querySelectorAll("[data-search-highlight]"))node.removeAttribute("data-search-highlight");
  target.dataset.searchHighlight="";if(!target.matches("button,a[href],input,select,textarea,summary,[tabindex]"))target.tabIndex=-1;target.focus({preventScroll:true});target.scrollIntoView({block:"center"});
  $("dashboardSearchResults").hidden=true;persistPreferences();
}
function drawDashboardSearch(){
  const query=$("dashboardSearch").value.trim(),root=$("dashboardSearchResults"),list=$("dashboardSearchList");list.replaceChildren();
  if(!query||!state){root.hidden=true;return}root.hidden=false;
  const words=searchWords(query),matches=dashboardSearchEntries.filter(e=>searchMatches(e.text,words));
  matches.sort((a,b)=>Number(!searchMatches(a.title,words))-Number(!searchMatches(b.title,words)));
  $("dashboardSearchCount").textContent=matches.length?matches.length+" match"+(matches.length===1?"":"es")+" in "+state.name:"No matches in this campaign.";
  for(const entry of matches.slice(0,dashboardSearchLimit)){
    const li=element("li"),button=element("button",undefined,"search-result");button.type="button";
    button.append(element("strong",entry.title),element("small",entry.section));
    const at=words.reduce((best,word)=>{const found=entry.body.toLocaleLowerCase().indexOf(word);return found<0?best:Math.min(best,found)},entry.body.length);
    const start=Math.max(0,at-45);button.append(element("span",(start?"…":"")+briefText(entry.body.slice(start),180)));
    button.onclick=()=>revealSearchResult(entry,words);li.append(button);list.append(li);
    button.onkeydown=event=>{const buttons=[...list.querySelectorAll("button")],i=buttons.indexOf(button);if(event.key==="ArrowDown"||event.key==="ArrowUp"){event.preventDefault();buttons[(i+(event.key==="ArrowDown"?1:buttons.length-1))%buttons.length].focus()}else if(event.key==="Escape"){$("dashboardSearch").focus();root.hidden=true}};
  }
  $("dashboardSearchMore").hidden=matches.length<=dashboardSearchLimit;
}
$("dashboardSearch").oninput=()=>{dashboardSearchLimit=40;drawDashboardSearch()};
$("dashboardSearch").onfocus=()=>drawDashboardSearch();

$("dashboardSearch").onkeydown=event=>{if(event.key==="Escape"){$("dashboardSearchResults").hidden=true}else if(event.key==="ArrowDown"){event.preventDefault();$("dashboardSearchList").querySelector("button")?.focus()}};
$("dashboardSearchForm").onsubmit=event=>{event.preventDefault();$("dashboardSearchList").querySelector("button")?.click()};
$("dashboardSearchClear").onclick=()=>{clearDashboardSearch();$("dashboardSearch").focus()};
$("dashboardSearchMore").onclick=()=>{dashboardSearchLimit+=40;drawDashboardSearch()};
document.addEventListener("pointerdown",event=>{if(!$("dashboardSearchBox").contains(event.target))$("dashboardSearchResults").hidden=true});
