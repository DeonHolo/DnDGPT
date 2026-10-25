/* Structured quest cards and owned image media; no automatic gameplay writes. */
function questStatus(row){return String(row.status||"active").toLowerCase().replace(/^complete$/,"completed")}
function renderReward(parent,title,reward,status){
  const box=element("section",undefined,"quest-reward");box.append(element("h4",title));
  if(reward?.summary)box.append(element("p",reward.summary));
  const list=element("ul");
  if(reward?.xp)list.append(element("li",reward.xp+" XP"));
  for(const [unit,amount]of Object.entries(reward?.currency||{}))if(amount)list.append(element("li",amount+" "+unit));
  for(const item of reward?.items||[])list.append(element("li",(item.name||"Equipment")+(item.rarity?" · "+item.rarity:"")));
  if(reward?.evolution_credits)list.append(element("li",reward.evolution_credits+" bankable Skill Evolution credit"+(reward.evolution_credits===1?"":"s")));
  if(list.children.length)box.append(list);else if(!reward?.summary)box.append(element("p","Reward terms have not been recorded.","muted"));
  if(status)box.append(element("small",status));parent.append(box);
}
function renderObjectives(parent,rows){
  const list=element("ul",undefined,"quest-objectives");
  for(const objective of rows.filter(row=>row.known_to_player!==false)){
    const status=objective.status||"pending",li=element("li",undefined,status==="done"?"done":"");
    const icon=element("span",status==="done"?"✓":status==="blocked"?"!":"○","objective-icon");icon.setAttribute("aria-hidden","true");
    const copy=element("div");copy.append(element("span",objective.text||"Objective"));
    const label=status==="done"?"Done":status==="in_progress"?"In progress":status==="blocked"?"Blocked":"Pending";
    copy.append(element("span",label+(objective.target?" · "+(objective.current||0)+" / "+objective.target:""),"objective-state"));
    if(objective.reward)renderReward(copy,"Bonus System reward",objective.reward,status==="done"?"Earned":"On completion");
    li.append(icon,copy);list.append(li);
  }parent.append(list);
}
function renderQuestCard(parent,quest){
  const card=element("article",undefined,"quest-card");card.dataset.questId=quest.id||"";
  const head=element("div",undefined,"quest-head");head.append(element("h3",quest.name||quest.title||"Quest"));
  head.append(element("span",questStatus(quest).replaceAll("_"," "),"quest-badge"));card.append(head);
  const type=[quest.quest_type,quest.difficulty].filter(Boolean).join(" · ");if(type)card.append(element("p",type,"eyebrow"));
  if(quest.quest_schema!==1||!Array.isArray(quest.objectives)){
    card.append(element("p","This older quest has no structured objective checklist yet.","muted"));
    const details=recordDetail(card,"Saved quest details","quest-legacy-"+quest.id);renderValue(details,quest);parent.append(card);return;
  }
  if(quest.description||quest.premise)card.append(element("p",quest.description||quest.premise));
  const required=quest.objectives.filter(row=>!row.optional),done=required.filter(row=>row.status==="done").length;
  card.append(element("p",done+" / "+required.length+" required objectives complete","quest-count"));
  const meter=element("progress",undefined,"quest-meter");meter.max=required.length;meter.value=done;meter.setAttribute("aria-label","Required objectives: "+done+" of "+required.length+" complete");card.append(meter);
  renderObjectives(card,required);
  const optional=quest.objectives.filter(row=>row.optional);
  if(optional.length)renderObjectives(recordDetail(card,"Optional bonus objectives","quest-optional-"+quest.id),optional);
  if(quest.finish_condition)card.append(element("p","Finish: "+quest.finish_condition,"muted"));
  renderReward(card,"System reward",quest.system_reward,quest.reward_status==="settled"?"Granted on completion":"Granted when required objectives are complete");
  if(quest.contract_payment){
    const pay=quest.contract_payment;renderReward(card,"Contract payment · "+pay.creditor,pay.reward,pay.status==="collected"?"Collected":pay.status==="unavailable"?"Unavailable":"Owed · "+pay.condition);
  }
  if(quest.progress_note)card.append(element("p",quest.progress_note,"muted"));
  const aftermath=state?.campaign_life?.aftermath?.find(row=>row.quest_id===quest.id);
  if(aftermath){const result=element("aside",undefined,"life-change");result.append(element("strong","After the quest"),element("p",aftermath.summary));card.append(result)}
  parent.append(card);
}
function renderQuests(parent,rows){
  rows=rows.filter(row=>row.known_to_player!==false);
  parent.replaceChildren();if(!rows.length){paragraph(parent,"No quests recorded.","muted");return}
  const active=rows.filter(row=>!["completed","failed","abandoned"].includes(questStatus(row)));
  for(const row of active)renderQuestCard(parent,row);
  for(const [statuses,label]of [[["completed"],"Completed"],[["failed","abandoned"],"Closed"]]){
    const archived=rows.filter(row=>statuses.includes(questStatus(row)));if(!archived.length)continue;
    const detail=recordDetail(parent,label+" · "+archived.length,"quests-archive-"+label.toLowerCase());detail.classList.add("quest-archive");
    for(const row of archived)renderQuestCard(detail,row);
  }
}
function renderEventChecks(next){
  const tracking=next.event_tracking;if(!tracking)return;
  const root=$("world-page-world")||$("world"),detail=recordDetail(root,"Event checks","world-event-checks");
  if(tracking.check_due)paragraph(detail,"An event check is pending for the latest meaningful transition.","pending");
  if(tracking.last_transition?.eligible===false)paragraph(detail,"Latest transition: no check · "+tracking.last_transition.reason,"muted");
  for(const row of [...(tracking.history||[])].reverse()){
    paragraph(detail,(row.context||"Travel")+" · "+row.chance+"% · d100 "+row.trigger_roll+" · "+(row.outcome==="event"?row.selected?.title:row.outcome==="no_event"?"No random event":"Prepared event unavailable"));
  }
}
let galleryCampaign=null,galleryItems=[],galleryLoaded=false,galleryBusy=false;
const galleryCache=new Map();
const galleryObserver=new IntersectionObserver(entries=>{for(const entry of entries)if(entry.isIntersecting){galleryObserver.unobserve(entry.target);loadGalleryThumb(entry.target)}});
function galleryReset(id){
  if(galleryCampaign===id)return;galleryCampaign=id;galleryItems=[];galleryLoaded=false;galleryCache.clear();galleryObserver.disconnect();
  const dialog=$("galleryDialog");if(dialog?.open)dialog.close();renderGallery();
}
function receiveGallery(data){
  if(!state||data.campaign_id!==state.id)return;
  galleryReset(state.id);
  if(Array.isArray(data.gallery_items)){galleryItems=data.gallery_items;galleryLoaded=true;}
  if(data.gallery_entry){galleryItems=[data.gallery_entry,...galleryItems.filter(row=>row.id!==data.gallery_entry.id)];}
  if(data.gallery_entry||Array.isArray(data.gallery_items))renderGallery();
}
async function refreshGallery(){
  if(!state)return;const id=state.id;galleryReset(id);
  try{await callTool("list_gallery_images",{campaign_id:id,include_removed:$("galleryRemoved")?.checked||false})}catch(error){notice("Gallery: "+error.message)}
}
async function galleryImage(id,size="thumbnail"){
  const key=galleryCampaign+":"+id+":"+size;if(galleryCache.has(key))return galleryCache.get(key);
  const campaign=galleryCampaign,result=await callTool("get_gallery_image",{campaign_id:campaign,image_id:id,size});
  const image=result?._meta?.gallery_image;
  if(typeof image!=="string"||!image.startsWith("data:image/webp;base64,"))throw new Error("Image data is unavailable");
  if(campaign!==state?.id)throw new Error("Campaign changed");
  if(galleryCache.size>=40)galleryCache.delete(galleryCache.keys().next().value);galleryCache.set(key,image);return image;
}
async function loadGalleryThumb(button){
  const img=button.querySelector("img");if(!img)return;
  try{const url=await galleryImage(button.dataset.imageId);if(img.isConnected)img.src=url}catch(error){if(img.isConnected)img.alt="Preview unavailable · "+error.message}
}
async function openGalleryImage(item){
  const dialog=$("galleryDialog"),image=$("galleryFullImage");$("galleryDialogTitle").textContent=item.title;image.alt=item.caption||item.title;image.removeAttribute("src");
  $("galleryDownload").hidden=true;$("galleryDownload").removeAttribute("href");dialog.dataset.imageId=item.id;
  $("galleryDialogCaption").textContent=item.caption||"";dialog.showModal();
  try{const url=await galleryImage(item.id,"full");if(dialog.open&&dialog.dataset.imageId===item.id){image.src=url;$("galleryDownload").hidden=false;$("galleryDownload").href=url;$("galleryDownload").download=(item.title||"campaign-image").replace(/[^a-z0-9_-]+/gi,"-")+".webp"}}catch(error){notice("Gallery: "+error.message)}
}
function renderGallery(){
  const root=$("galleryGrid");if(!root)return;root.replaceChildren();galleryObserver.disconnect();
  const removed=$("galleryRemoved")?.checked,shown=galleryItems.filter(item=>removed||!item.removed);
  const count=galleryItems.filter(item=>!item.removed).length;
  $("galleryPreview").textContent=galleryLoaded?count+" saved image"+(count===1?"":"s"):"Saved campaign images";
  if(!shown.length){paragraph(root,galleryLoaded?"No saved images yet. Ask ChatGPT to save an image, or add one here.":"Open Gallery to load saved images.","muted");refreshDashboardSearch();return}
  for(const item of shown){
    const card=element("article",undefined,"gallery-card"),button=element("button",undefined,"gallery-open");button.type="button";button.dataset.imageId=item.id;button.setAttribute("aria-label","View image: "+item.title);
    const img=element("img");img.alt=item.caption||item.title;img.width=400;img.height=200;img.loading="lazy";button.append(img);button.onclick=()=>openGalleryImage(item);card.append(button,element("h3",item.title));
    if(item.caption)card.append(element("p",item.caption));
    card.append(element("p",({generated:"Generated",web:"From the web",upload:"Uploaded"}[item.source_kind]||"Image")+(item.scene_ref?" · "+item.scene_ref:""),"gallery-source"));
    if(item.credit)card.append(element("p",item.credit,"gallery-source"));
    if(item.source_url?.startsWith("https://")){const source=element("a","Source / credit");source.href=item.source_url;source.target="_blank";source.rel="noopener noreferrer";card.append(source)}
    const remove=element("button",item.removed?"Restore image":"Remove from Gallery","gallery-remove");remove.type="button";remove.onclick=async()=>{remove.disabled=true;try{await callTool("set_gallery_image_removed",{campaign_id:state.id,image_id:item.id,removed:!item.removed})}catch(error){notice(error.message);remove.disabled=false}};card.append(remove);root.append(card);galleryObserver.observe(button);
  }
  refreshDashboardSearch();
}
async function saveGalleryFile(file,title,caption){
  const common={campaign_id:state.id,action_id:"gallery-"+crypto.randomUUID(),title,caption};
  if(window.openai?.uploadFile&&window.openai?.getFileDownloadUrl){
    const uploaded=await window.openai.uploadFile(file),url=await window.openai.getFileDownloadUrl({fileId:uploaded.fileId});
    return callTool("save_gallery_image",{...common,source_kind:"upload",image:{download_url:url.downloadUrl,file_id:uploaded.fileId,mime_type:file.type,file_name:file.name}});
  }
  if(file.size>8*1024*1024)throw new Error("Images can be at most 8 MB");
  const bitmap=await createImageBitmap(file);if(bitmap.width*bitmap.height>20000000){bitmap.close();throw new Error("Use an image under 20 megapixels")}
  const scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height)),canvas=document.createElement("canvas");canvas.width=Math.round(bitmap.width*scale);canvas.height=Math.round(bitmap.height*scale);canvas.getContext("2d").drawImage(bitmap,0,0,canvas.width,canvas.height);bitmap.close();
  const data=canvas.toDataURL("image/webp",.82);return callTool("upload_gallery_image",{...common,image_data:data});
}
$("galleryRefresh").onclick=refreshGallery;$("galleryRemoved").onchange=refreshGallery;
$("galleryForm").onsubmit=async event=>{
  event.preventDefault();if(!state||galleryBusy)return;galleryBusy=true;$("gallerySave").disabled=true;
  const title=$("galleryTitle").value.trim(),caption=$("galleryCaption").value.trim(),url=$("galleryUrl").value.trim(),file=$("galleryFile").files[0];
  try{
    if(Boolean(url)===Boolean(file))throw new Error("Choose one file or enter one direct image URL");
    if(file)await saveGalleryFile(file,title,caption);else await callTool("save_gallery_url",{campaign_id:state.id,action_id:"gallery-"+crypto.randomUUID(),title,caption,image_url:url,source_url:$("gallerySource").value.trim(),credit:$("galleryCredit").value.trim()});
    $("galleryForm").reset();await refreshGallery();notice("Image saved to Gallery.");
  }catch(error){notice("Gallery: "+error.message)}finally{galleryBusy=false;$("gallerySave").disabled=false}
};
$("galleryChooseFiles").onclick=async()=>{
  if(!state||!window.openai?.selectFiles||!window.openai?.getFileDownloadUrl)return;
  try{const files=await window.openai.selectFiles();for(const file of files.slice(0,8)){
    const url=await window.openai.getFileDownloadUrl({fileId:file.fileId});await callTool("save_gallery_image",{campaign_id:state.id,action_id:"gallery-"+crypto.randomUUID(),title:file.fileName||"Campaign image",source_kind:"upload",image:{download_url:url.downloadUrl,file_id:file.fileId,mime_type:file.mimeType||"",file_name:file.fileName||""}});
  }await refreshGallery()}catch(error){notice("Gallery: "+error.message)}
};
$("galleryDialogClose").onclick=()=>$("galleryDialog").close();
document.addEventListener("companion:page",event=>{if(event.detail?.id==="gallery"){
  $("galleryChooseFiles").hidden=!(window.openai?.selectFiles&&window.openai?.getFileDownloadUrl);galleryReset(state?.id||null);if(!galleryLoaded)refreshGallery();
}});
document.addEventListener("companion:campaign",event=>{
  const id=event.detail?.id||null,changed=galleryCampaign!==id;galleryReset(id);
  if(changed&&id&&!$("page-gallery").hidden)refreshGallery();
});
