function lifeCard(parent,title,description){
  const card=element("article",undefined,"life-card");card.append(element("h3",title));
  if(description)paragraph(card,description);parent.append(card);return card;
}
function renderCampaignLife(next){
  const root=$("world-page-living");if(!root)return;root.replaceChildren();
  const life=next.campaign_life||{},actors=life.actors||[],places=life.places||[];
  root.append(element("h3","People & places","group"));
  const pacing=life.pacing||{mode:"scene"},pace=lifeCard(root,"Your pace",pacing.objective||"Choose how much routine activity to resolve together.");
  paragraph(pace,pacing.stop_reason||("Current pace: "+({scene:"scene by scene",journey:"journey",expedition:"expedition"}[pacing.mode]||"scene by scene")),"muted");
  const controls=element("div",undefined,"life-actions");
  for(const [label,request]of [["Scene by scene","Continue scene by scene, stopping for my decisions."],["Travel to next decision","Resolve routine travel toward my stated destination together, stopping for a new danger, resource decision or meaningful choice."],["Plan an expedition","Help set an expedition objective and a fictional-time horizon, then carry out only the routine actions I authorize."]]){
    const button=element("button",label);button.type="button";button.disabled=next.paused||next.level_up_freeze||next.phase!=="adventure";
    button.onclick=()=>sendPrompt(request+" Campaign: "+next.name+" ("+next.id+"). Keep all actual checks and costs. My pace selection alone does not choose a destination or resolve a pending decision.");controls.append(button);
  }pace.append(controls);
  const people=element("div",undefined,"life-grid");root.append(element("h3","People & factions","group"),people);
  if(!actors.length)paragraph(people,"People and rival factions appear here as their history is recorded.","muted");
  for(const actor of actors){
    const card=lifeCard(people,actor.name,actor.description),relation=actor.relationship||{};
    if(relation.known_to_player!==false)paragraph(card,(relation.stance||"neutral")+(relation.reason?" · "+relation.reason:""),"life-meta");
    const detail=recordDetail(card,"History & character","life-actor-"+actor.id);
    if(actor.traits?.length)paragraph(detail,actor.traits.join(" · "));
    if(actor.goal)paragraph(detail,"Goal · "+actor.goal);
    if(actor.preferred_approach)paragraph(detail,"Approach · "+actor.preferred_approach);
    const observations=(actor.observations||[]).filter(r=>r.known_to_player!==false);
    for(const row of observations)paragraph(detail,row.summary,"life-memory");
    for(const row of (actor.commitments||[]).filter(r=>r.known_to_player!==false))paragraph(detail,row.status+" · "+row.text,"life-promise");
  }
  root.append(element("h3",next.game_id==="sovereign-system"?"Territory & routes":"Known places & routes","group"));
  const terrain=element("div",undefined,"life-grid");root.append(terrain);
  if(!places.length)paragraph(terrain,"Discovered places, routes and lasting changes appear here.","muted");
  const names=new Map(places.map(p=>[p.id,p.name]));
  for(const place of places){
    const card=lifeCard(terrain,place.name,place.description);card.id="life-place-"+encodeURIComponent(place.id);
    if(place.controller)paragraph(card,"Held by · "+place.controller,"life-meta");
    if(place.last_change)paragraph(card,place.last_change,"life-change");
    for(const feature of place.features||[])paragraph(card,feature.name+" · "+feature.description);
    if(place.links?.length){const routes=element("p",undefined,"life-routes");routes.append(document.createTextNode("Routes · "));
      for(const [i,id]of place.links.entries()){if(i)routes.append(document.createTextNode(" / "));const a=element("a",names.get(id)||id);a.href="#life-place-"+encodeURIComponent(id);a.onclick=e=>{e.preventDefault();$("life-place-"+encodeURIComponent(id))?.scrollIntoView({block:"nearest"})};routes.append(a)}card.append(routes);
    }
  }
  const s=next.sovereignty;
  if(s){const fronts=lifeCard(root,"Active fronts & expeditions");
    for(const f of s.fronts||[])if(f.status==="active")paragraph(fronts,f.name+" · "+f.objective+" · "+f.player_progress+" / "+f.target_progress);
    for(const op of s.operations||[])if(op.status==="active")paragraph(fronts,op.name||op.objective);
    if(!fronts.querySelector("p"))paragraph(fronts,"No active fronts or expeditions.","muted");
  }
  if(life.aftermath?.length){root.append(element("h3","After the quest","group"));for(const row of life.aftermath.slice(-12).reverse())lifeCard(root,next.quest_log.find(q=>q.id===row.quest_id)?.name||"Resolved quest",row.summary)}
  if(life.developments?.length){const changes=recordDetail(root,"Acquired capabilities","life-developments");for(const row of life.developments.slice(-20).reverse())paragraph(changes,row.summary)}
}
