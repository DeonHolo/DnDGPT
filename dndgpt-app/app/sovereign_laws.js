function usesSovereignLaws(campaign) {
  return campaign.rules_profile === "sovereign-laws-2026-11-05";
}

function renderLawsOwner(parent, owner, label) {
  if (!owner || owner.known_to_player === false || owner.known === false) return;
  const card = sovereigntyCard(parent, owner.name, label, owner.description);
  card.dataset.lawsOwner = owner.id;
  if (owner.rarity) card.querySelector("h3").classList.add("rarity-" + owner.rarity);
  renderFacts(card, [
    ["Origin", owner.history], ["Deed", owner.deed], ["Known by", owner.recognition],
    ["What you can do", owner.effect], ["Where", owner.location], ["Orders", owner.orders],
    ["Condition", owner.condition], ["Objective", owner.objective], ["Outcome", owner.outcome]
  ]);
  for (const power of [...owner.capabilities || [], ...owner.abilities || []]) {
    if (power.known_to_player !== false) sovereignEffect(card, power, owner.id + "-" + power.id);
  }
  const upgrades = (owner.upgrades || []).filter(item => item.known_to_player !== false);
  if (upgrades.length) {
    const history = recordDetail(card, "Earned upgrades · " + upgrades.length, "laws-upgrades-" + owner.id);
    for (const upgrade of upgrades) {
      history.append(element("h4", upgrade.name, "rarity-" + upgrade.rarity));
      paragraph(history, upgrade.effect);
    }
  }
  return card;
}

function renderLawsCampaign(next) {
  const character = next.character;
  const body = next.creation.sovereign_body;
  const sovereignty = next.sovereignty;
  const owners = [...sovereignty.commanders, ...sovereignty.formations, ...next.summons];
  const allies = owners.filter(actor => actor.side !== "enemy" && activeActor(actor));
  const enemies = [...next.enemies, ...owners.filter(actor => actor.side === "enemy")].filter(enemy => activeActor(enemy, true));
  $("title-skills").textContent = "Laws & Developments";
  $("nav-skills").querySelector(".nav-title").textContent = "Laws & Developments";
  $("hero").textContent = character.name + " · " + character.class_name;
  $("resources").replaceChildren();
  $("characterPreview").textContent = character.rarity + (body ? " · " + body.form : " · Creation");
  $("skillsPreview").textContent = next.abilities.length + " Laws";
  $("healthPreview").textContent = next.conditions.length + " recorded conditions";
  $("summonsPreview").textContent = allies.length + (allies.length === 1 ? " ally · " : " allies · ") + enemies.length + " threats";
  $("equipmentPreview").textContent = next.inventory.length + (next.inventory.length === 1 ? " item" : " items");
  $("questsPreview").textContent = next.quest_log.filter(q => questStatus(q) === "active").length + " active";
  $("worldPreview").textContent = next.current_location;
  $("sovereigntyPreview").textContent = sovereignty.domain.name;
  $("progress").textContent = next.paused ? "Paused" : next.phase === "adventure" ? "In play" : "Character draft";
  $("location").textContent = next.current_location;
  for (const key of ["character", "health", "summons", "equipment", "quests", "world", "sovereignty"]) {
    $(key).replaceChildren();
  }
  paragraph($("character"), character.name, "page-lead");
  paragraph($("character"), character.class_name + " · " + character.rarity, "muted");
  paragraph($("character"), "Luck · " + character.attributes.LCK, "muted");
  const story = recordDetail($("character"), "Your story", "character-story");
  story.className = "character-story";
  const copy = element("div", undefined, "story-copy");
  paragraph(copy, character.story_summary || "Your story takes shape during creation.");
  story.append(copy);
  renderLawsOwner($("character"), next.creation.origin, "Origin");
  renderLawsOwner($("character"), next.creation.title, "Title");
  renderSkills(next.abilities);
  renderRecords($("health"), next.conditions, "Your current condition is clear.");
  for (const ally of allies) renderLawsOwner($("summons"), ally, "Ally");
  for (const enemy of enemies) renderLawsOwner($("summons"), enemy, "Threat");
  if (!allies.length && !enemies.length) paragraph($("summons"), "Your allies and current threats appear here.", "muted");
  for (const item of next.inventory) renderLawsOwner($("equipment"), item, item.holder || item.location || "Gear");
  if (!next.inventory.length) paragraph($("equipment"), "Your acquired gear appears here.", "muted");
  renderQuests($("quests"), next.quest_log);
  renderSovereignBody($("sovereignty"), next);
  renderLawsOwner($("sovereignty"), sovereignty.domain, "Domain");
  for (const [key, label] of [["holdings", "Holding"], ["assets", "Asset"], ["encounters", "Encounter"]]) {
    for (const item of sovereignty.domain[key] || []) renderLawsOwner($("sovereignty"), item, label);
  }
  for (const group of [sovereignty.commanders, sovereignty.formations]) {
    for (const owner of group) renderLawsOwner($("sovereignty"), owner, owner.side === "enemy" ? "Opposition" : "Your allies");
  }
  for (const [key, label] of [["operations", "Standing orders"], ["fronts", "Current conflict"]]) {
    for (const item of sovereignty[key]) renderLawsOwner($("sovereignty"), item, label);
  }
  renderWorld(next);
  renderCampaignLife(next);
  renderCampaignFocus(next);
  renderChoices();
  restorePreferences();
  updateSaveTools();
  refreshDashboardSearch();
}
