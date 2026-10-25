/* Read-only roster projection. A roster refresh never advances summon clocks. */
let actorSelections={},actorOpeners=new Map();
const playerStatuses={player_victory:"Victory",enemy_victory:"Defeat",mutual_destruction:"Both forces lost",active:"Active",inactive:"Inactive",draft:"Preparing",character_draft:"Character creation",in_progress:"In progress",completed:"Completed",done:"Complete",pending:"Pending",routed:"Routed",wounded:"Wounded"};
function playerStatus(value){return playerStatuses[String(value).toLowerCase()]||fieldLabel(String(value))}
function playerText(value){return String(value)
  .replace(/\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b/g,playerStatus)
  .replace(/\b(Level|HP|MP|DEF|DC|XP|speed|per|over|for|every)(?=\d)/gi,"$1 ")
  .replace(/(\d)(min(?:ute)?s?|hours?|seconds?|rounds?|m|kg)\b/gi,"$1 $2")
  .replace(/\bceil\(([^()]+)\/2\)/g,"half of $1, rounded up")}
function lastingActor(actor){return actor.permanent===true||actor.persistent===true||String(actor.duration).toLowerCase()==="permanent"||/permanent|commander/.test(actor.kind||"")}
function activeActor(actor,enemy=false){
  if(actor.known_to_player===false||actor.active===false||["dead","defeated","destroyed","expired","dismissed","inactive","retired","withdrawn","departed","escaped","routed","surrendered","captured"].includes(String(actor.status||"").toLowerCase()))return false;
  if(["dead","expired","dismissed","destroyed"].some(key=>actor[key]===true))return false;
  if(actor.hp!==undefined&&actor.hp!==null&&Number(actor.hp)<=0&&(enemy||!(lastingActor(actor)||actor.recoverable===true||actor.recovery||actor.revival)))return false;
  if(!lastingActor(actor)&&["rounds_remaining","remaining_rounds","duration_remaining","seconds_remaining"].some(key=>typeof actor[key]==="number"&&actor[key]<=0))return false;
  return true;
}
function actorStatus(actor){return actor.hp!==undefined&&actor.hp!==null&&Number(actor.hp)<=0?"Downed":playerStatus(actor.status||"active")}
function actorSummary(actor){
  const parts=[actor.hp===undefined?null:"HP "+actor.hp+(actor.hp_max===undefined?"":" / "+actor.hp_max),actorStatus(actor)];
  const rounds=actor.rounds_remaining??actor.remaining_rounds;
  if(typeof rounds==="number")parts.push(rounds+" rounds left");
  else if(actor.duration)parts.push(actor.duration);
  return parts.filter(Boolean).join(" · ");
}
function renderActorRoster(parent,records,scope){
  if(!records.length){paragraph(parent,scope==="enemy"?"No active enemies.":"No allies currently in the field.","muted");return}
  const {index,article}=readingLayout(parent);index.classList.add("actor-index");article.classList.add("actor-inspector");
  index.setAttribute("aria-label",scope==="enemy"?"Active enemies":"Allies in the field");
  const buttons=[],groups=new Map();
  for(const [position,actor]of records.entries()){
    const key=actor.id||scope+"-"+position,button=element("button",undefined,"index-entry");button.type="button";button.dataset.actorId=key;
    button.append(element("span",actor.name||"Unnamed creature","entry-name"),element("span",actorSummary(actor),"entry-meta"));
    // Group only explicitly related temporary instances; same names alone are insufficient.
    const family=!lastingActor(actor)&&(actor.summon_type_id||actor.template_id||actor.source_ability_id);
    const groupKey=family&&family+":"+(actor.name||"");
    if(groupKey&&!groups.has(groupKey)){const peers=records.filter(row=>!lastingActor(row)&&(row.summon_type_id||row.template_id||row.source_ability_id)===family&&row.name===actor.name);if(peers.length>1){const group=element("details",undefined,"actor-group");group.append(element("summary",actor.name+" × "+peers.length));index.append(group);groups.set(groupKey,group)}}
    (groups.get(groupKey)||index).append(button);buttons.push(button);
    const select=()=>{actorSelections[scope]=key;for(const item of buttons)item.setAttribute("aria-pressed",String(item===button));article.replaceChildren();renderActors(article,[actor],scope);paragraph(article,actorStatus(actor),"actor-meta");if(button.closest("details"))button.closest("details").open=true;return article};
    button.onclick=select;actorOpeners.set(scope+":"+key,select);
    button.onkeydown=event=>{if(!["ArrowDown","ArrowUp","Home","End"].includes(event.key)||event.altKey||event.ctrlKey||event.metaKey)return;event.preventDefault();const i=buttons.indexOf(button),target=event.key==="Home"?0:event.key==="End"?buttons.length-1:(i+(event.key==="ArrowDown"?1:buttons.length-1))%buttons.length;buttons[target].click();buttons[target].focus()};
  }
  (buttons.find(button=>button.dataset.actorId===actorSelections[scope])||buttons[0]).click();
}
function openSearchActor(actor,enemy){selectCompanionPage("summons");selectCombatTab(enemy?"combat":"summons");return actorOpeners.get((enemy?"enemy":"summon")+":"+actor.id)?.()}
