// On-demand save tools. None of these controls add calls to a normal gameplay turn.
let historyPage=null, importFile=null, importAction=null, saveToolsCampaign=null, historyLoading=false;
const correctionFields={"character.name":"Character name","character.class_name":"Class name",
  "character.title":"Title","character.background":"Background","character.story_summary":"Your story",
  "character.hp":"HP","character.mp":"MP","current_location":"Current location"};

function showSaveChanges(root,report){
  root.replaceChildren();
  if(report?.withheld_sections?.length)paragraph(root,"Recorded changes also affect "+report.withheld_sections.map(key=>key.replaceAll("_"," ")).join(", ")+". Hidden or internal details are not displayed.","muted");
  if(!report?.changes?.length){paragraph(root,"No changes to displayed character or campaign fields.","muted");return}
  for(const change of report.changes){
    const box=element("article",undefined,"save-change"),facts=element("dl");
    box.append(element("h4",change.label));
    for(const [label,key]of [["Before","before"],["After","after"]]){
      const value=change[key];facts.append(element("dt",label),element("dd",value.text+(value.truncated?" … (excerpt)":"")));
    }
    box.append(facts);root.append(box);
  }
  if(report.truncated)paragraph(root,"Showing "+report.changes.length+" of "+report.change_count+" changed fields.","muted");
}

function updateSaveTools(){
  const chat=state?.mode==="chat";
  for(const id of ["downloadCampaign","loadHistory","correctionPreview"])$(id).disabled=!chat||busy||deleting||syncIssue;
  if(saveToolsCampaign!==state?.id){
    saveToolsCampaign=state?.id;historyPage=null;$("historyList").replaceChildren();$("historyChanges").replaceChildren();
    $("historyMore").hidden=true;$("historyStatus").textContent="History loads only when requested.";
    $("exportDownload").replaceChildren();$("exportDownload").hidden=true;
  }
  const root=$("resumeBrief");root.replaceChildren();
  const brief=state?.resume_brief;
  if(!brief){paragraph(root,"Select a saved campaign to read its continuity brief.","muted");return}
  paragraph(root,brief.current_location+" · save "+brief.version+(brief.level_up_freeze?" · advancement frozen":brief.paused?" · paused":" · awaiting your next action"));
  for(const [label,key]of [["Scene","scene"],["Your last intent","last_player_intent"],["Last action","last_action"],
      ["Outcome","outcome"],["Connection","transition"],["Pending decision","pending_decision"]]){
    if(brief[key]){const p=element("p");p.append(element("strong",label+": "),document.createTextNode(brief[key]));root.append(p)}
  }
  for(const [label,key]of [["Unresolved threads","unresolved_threads"],["NPC commitments","npc_commitments"]]){
    if(brief[key]?.length){root.append(element("strong",label));const list=element("ul");list.append(...brief[key].map(text=>element("li",text)));root.append(list)}
  }
  if(brief.additional_threads||brief.additional_commitments||brief.excerpted_fields?.length)
    paragraph(root,"This compact brief contains excerpts. Full saved continuity includes "+brief.additional_threads+" more threads and "+brief.additional_commitments+" more commitments; the GM can retrieve the full state when needed.","muted");
  if(brief.missing_continuity)paragraph(root,"This older save has no detailed continuity note yet. Ask the GM to reconstruct it from established records; missing details should stay unknown.","muted");
  paragraph(root,"Reading this brief does not advance time or start/resume play.","muted");
}

async function loadSaveHistory(more=false){
  if(!state||historyLoading)return;
  const selected=state.id;historyLoading=true;$("loadHistory").disabled=true;
  try{
    const args={campaign_id:selected,limit:20};if(more&&historyPage?.next_before)args.before=historyPage.next_before;
    const result=await callTool("list_chat_versions",args);
    if(state?.id!==selected)return;
    historyPage=result.structuredContent;
    if(!more)$("historyList").replaceChildren();
    for(const entry of historyPage.versions){
      const item=element("li"),button=element("button","Version "+entry.version);button.type="button";
      button.title=entry.summary;button.setAttribute("aria-pressed","false");
      button.onclick=async()=>{
        try{
          const response=await callTool("compare_chat_version",{campaign_id:selected,version:entry.version});
          if(state?.id!==selected)return;
          for(const other of $("historyList").querySelectorAll("button"))other.setAttribute("aria-pressed",String(other===button));
          $("historyStatus").textContent="Version "+entry.version+" · "+entry.summary+" · "+entry.location;
          showSaveChanges($("historyChanges"),response.structuredContent);
        }catch(error){notice(error.message)}
      };item.append(button);$("historyList").append(item);
    }
    $("historyStatus").textContent="Current save: version "+historyPage.current_version+". Select a version to see what changed when it was saved.";
    $("historyMore").hidden=!historyPage.next_before;
  }catch(error){notice(error.message)}finally{historyLoading=false;updateSaveTools()}
}

async function downloadCampaign(){
  if(!state)return;
  const selected=state.id;
  try{
    const result=(await callTool("export_campaign",{campaign_id:selected})).structuredContent;
    if(state?.id!==selected)return;
    const encoded=JSON.stringify(result.archive,null,2),blob=new Blob([encoded],{type:"application/json"}),url=URL.createObjectURL(blob);
    const link=element("a","Download campaign file");link.href=url;link.download=result.filename;
    const fallback=element("details"),copy=element("button","Copy campaign JSON"),text=element("textarea");
    fallback.append(element("summary","Copy JSON if downloads are unavailable"));
    paragraph(fallback,"Save this exact JSON in a local text file named "+result.filename+". Keep it private; it includes stored campaign and setting records.");
    text.value=encoded;text.readOnly=true;text.rows=6;text.setAttribute("aria-label","Portable campaign JSON");copy.type="button";
    copy.onclick=async()=>{try{await navigator.clipboard.writeText(encoded);notice("Campaign JSON copied. Save it as "+result.filename)}catch{fallback.open=true;text.focus();text.select();notice("Campaign JSON selected. Copy it and save as "+result.filename)}};
    fallback.append(copy,text);$("exportDownload").replaceChildren(link,fallback);$("exportDownload").hidden=false;link.click();
    notice("Campaign export prepared. Use the file link or copyable JSON. Server history remains with the original campaign.");
    setTimeout(()=>{URL.revokeObjectURL(url);link.remove()},120000);
  }catch(error){notice(error.message)}
}

async function previewImport(){
  const file=$("campaignFile").files?.[0];importFile=null;importAction=null;$("importReview").hidden=true;
  if(!file)return;
  if(file.size>2200000){notice("This file exceeds the campaign export size limit.");return}
  try{
    const parsed=JSON.parse(await file.text());
    const preview=(await callTool("preview_campaign_import",{archive:parsed})).structuredContent;
    importFile=parsed;importAction="restore-"+crypto.randomUUID();
    $("importDescription").textContent=preview.source_name+" · source version "+preview.source_version+" · "+preview.character_name+" · "+preview.class_name+" · "+preview.location;
    $("importNotice").textContent=preview.notice;$("importReview").hidden=false;$("confirmImport").disabled=false;
  }catch(error){notice("Could not read the campaign export: "+error.message)}
}

async function confirmImport(){
  if(!importFile||!importAction)return;
  $("confirmImport").disabled=true;
  try{
    const result=(await callTool("import_campaign",{archive:importFile,action_id:importAction,confirm_restore:true})).structuredContent;
    await callTool("render_dashboard",{campaign_id:result.campaign.id});
    importFile=null;importAction=null;$("importReview").hidden=true;$("campaignFile").value="";
    notice("Restored a separate paused campaign. Review its brief; continuing requires your next explicit action.");
  }catch(error){notice(error.message+". Retry this same restore if delivery was uncertain.");$("confirmImport").disabled=false}
}

async function previewCorrection(){
  if(!state)return;
  const field=$("correctionField").value,reason=$("correctionReason").value.trim();
  let value=$("correctionValue").value;
  if(!reason){notice("Explain what needs correcting before reviewing the change.");return}
  if(["character.hp","character.mp"].includes(field)){
    if(!/^\d+$/.test(value.trim())){notice("Enter a whole resource value of zero or more.");return}value=Number(value);
  }
  const changes=field.startsWith("character.")?{character:{[field.slice(10)]:value}}:{[field]:value};
  try{
    await callTool("propose_action",{campaign_id:state.id,action_id:"correct-"+crypto.randomUUID(),
      expected_version:state.version,kind:"correct_chat_state",payload:{changes,reason}});
    $("approval").scrollIntoView({block:"nearest"});notice("Review the proposed correction. Your saved game has not changed.");
  }catch(error){notice(error.message)}
}

for(const [key,label]of Object.entries(correctionFields)){const option=element("option",label);option.value=key;$("correctionField").append(option)}
$("correctionField").onchange=()=>{
  const field=$("correctionField").value;$("correctionValue").value=field.startsWith("character.")?state?.character?.[field.slice(10)]??"":state?.[field]??"";
};
$("saveTools").addEventListener("toggle",()=>{if($("saveTools").open&&!$("correctionValue").value)$("correctionField").onchange()});
$("loadHistory").onclick=()=>loadSaveHistory(false);$("historyMore").onclick=()=>loadSaveHistory(true);
$("downloadCampaign").onclick=downloadCampaign;$("campaignFile").onchange=previewImport;$("confirmImport").onclick=confirmImport;
$("cancelImport").onclick=()=>{importFile=null;importAction=null;$("importReview").hidden=true;$("campaignFile").value=""};
$("correctionPreview").onclick=previewCorrection;
