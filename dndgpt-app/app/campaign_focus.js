function renderCampaignFocus(next){
  const root=$("world-page-objectives");if(!root)return;root.replaceChildren();
  const focuses={mixed:"Mixed", "hunt-explore":"Hunt & Explore", conquest:"Conquest"};
  const dialogues={normal:"Normal",minimal:"Minimal","on-request":"On request"};
  const saved={focus:"mixed",dialogue:"normal",...(next.campaign_preferences||{})};
  const settings=lifeCard(root,"Campaign focus");
  paragraph(settings,"Saved · "+focuses[saved.focus]+" · Dialogue: "+dialogues[saved.dialogue],"life-meta");
  const form=element("form",undefined,"focus-form");
  for(const [key,title,choices]of [["focus","Adventure focus",focuses],["dialogue","Dialogue",dialogues]]){
    const field=element("div"),label=element("label",title),wrapper=element("span",undefined,"select-field"),select=element("select");
    select.id="campaign-"+key;label.htmlFor=select.id;
    for(const [value,name]of Object.entries(choices)){const option=element("option",name);option.value=value;select.append(option)}
    select.value=saved[key];select.disabled=next.mode!=="chat";wrapper.append(select);field.append(label,wrapper);form.append(field);
  }
  const submit=element("button","Save preferences in chat");submit.type="submit";submit.disabled=next.mode!=="chat";form.append(submit);
  form.onsubmit=event=>{event.preventDefault();sendPrompt("Save my campaign preferences with save_chat_update: "+JSON.stringify({campaign_preferences:{focus:$("campaign-focus").value,dialogue:$("campaign-dialogue").value}})+". This request changes preferences only. Preserve the current time, pause, advancement freeze, build, pending decisions and all gameplay outcomes. Do not begin or resolve an action.")};
  settings.append(form);paragraph(settings,"Changes are saved when your GM processes the request. You can also set these preferences directly in chat.","life-meta");
  const active=(next.quest_log||[]).filter(q=>q.known_to_player!==false&&!['completed','failed','abandoned'].includes(questStatus(q)));
  root.append(element("h3","Current objectives","group"));
  if(!active.length)paragraph(root,"Your next recorded hunt, conquest or quest will appear here.","muted");
  for(const quest of active){
    const card=lifeCard(root,quest.name||quest.title||"Quest");card.dataset.focusQuest=quest.id;
    paragraph(card,({hunt:"Hunt",conquest:"Conquest"}[quest.activity]||"Quest")+" · "+questStatus(quest),"life-meta");
    if(quest.target)paragraph(card,"Target · "+quest.target);
    if(quest.known_opposition)paragraph(card,"Known opposition · "+quest.known_opposition);
    const objectives=(quest.objectives||[]).filter(o=>o.known_to_player!==false);
    if(objectives.length)renderObjectives(card,objectives);
    if(quest.finish_condition)paragraph(card,"Finish · "+quest.finish_condition);
    if(quest.victory_benefit)paragraph(card,"Expected benefit · "+quest.victory_benefit,"life-change");
    if(quest.system_reward)renderReward(recordDetail(card,"System reward","focus-reward-"+quest.id),"On completion",quest.system_reward);
  }
  const known=(next.campaign_life?.places||[]).filter(p=>p.controller||p.features?.length);
  if(known.length){
    const places=lifeCard(root,"Places changed by your actions");
    for(const place of known){paragraph(places,place.name+(place.controller?" · Held by "+place.controller:""));for(const feature of place.features||[])paragraph(places,feature.name+" · "+feature.description,"life-meta")}
  }
  const fronts=(next.sovereignty?.fronts||[]).filter(f=>f.known!==false&&f.status==="active");
  if(fronts.length){const card=lifeCard(root,"Active fronts");for(const f of fronts)paragraph(card,f.name+" · "+f.objective+" · "+f.player_progress+" / "+f.target_progress)}
}
