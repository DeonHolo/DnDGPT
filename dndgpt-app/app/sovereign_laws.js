function usesSovereignLaws(campaign) {
  return campaign.rules_profile === "sovereign-laws-2026-11-05";
}

function lawsText(value, depth = 0) {
  if (depth > 8 || value?.known_to_player === false || value?.known === false) return "";
  if (typeof value === "string") return value.trim();
  if (Array.isArray(value)) return value.map(item => lawsText(item, depth + 1)).filter(Boolean).join("\n");
  if (!value || typeof value !== "object") return "";
  for (const key of ["mechanics_display", "mechanics", "full_rules", "effect", "effects", "rules", "text", "content", "description", "summary", "simple", "details", "benefit", "benefits"]) {
    const copy = lawsText(value[key], depth + 1);
    if (copy) return copy;
  }
  return "";
}

function lawsRows(value) {
  if (Array.isArray(value)) return value;
  if (typeof value === "string") return [value];
  if (!value || typeof value !== "object") return [];
  if (value.id || value.name || value.title || value.label || value.effect || value.text) return [value];
  return Object.entries(value).map(([name, item]) => typeof item === "string" ? {name, effect:item} : {name, ...item});
}

function renderLawsAppearance(parent, record, key, title = "Appearance") {
  const copy = lawsText(record.appearance || record.visual_description || record.look || record.manifestation || record.visual || record.description);
  if (!copy) { paragraph(parent, "Appearance hasn't been added to this save yet.", "muted"); return; }
  const detail = recordDetail(parent, title, key);
  detail.classList.add("laws-appearance");
  renderValue(detail, copy);
  return detail;
}

function lawsSovereigntyPanels(root) {
  const tabs = element("div", undefined, "sovereign-tabs");
  tabs.setAttribute("role", "tablist"); tabs.setAttribute("aria-label", "Sovereignty");
  root.append(tabs);
  const panels = {}, buttons = [];
  for (const [id, title] of [["domain", "Domain"], ["commanders", "General"], ["forces", "Army / Minions"]]) {
    const button = element("button", title), panel = element("section");
    button.type = "button"; button.id = "sovereign-tab-" + id;
    button.setAttribute("role", "tab"); button.setAttribute("aria-controls", "sovereign-panel-" + id);
    panel.id = "sovereign-panel-" + id; panel.dataset.lawsTab = id;
    panel.setAttribute("role", "tabpanel"); panel.setAttribute("aria-labelledby", button.id);
    panels[id] = panel; buttons.push(button); tabs.append(button); root.append(panel);
    button.onclick = () => {
      sovereignTab = id;
      for (const control of buttons) { const active = control === button; control.setAttribute("aria-selected", String(active)); control.tabIndex = active ? 0 : -1; }
      for (const [key, node] of Object.entries(panels)) node.hidden = key !== id;
    };
    button.onkeydown = event => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      const index = event.key === "Home" ? 0 : event.key === "End" ? buttons.length - 1 : (buttons.indexOf(button) + (event.key === "ArrowRight" ? 1 : -1) + buttons.length) % buttons.length;
      buttons[index].click(); buttons[index].focus();
    };
  }
  (buttons.find(button => button.id === "sovereign-tab-" + sovereignTab) || buttons[0]).click();
  return panels;
}

function openLawsSovereigntyCard(node) {
  const tab = node.closest("[data-laws-tab]")?.dataset.lawsTab;
  if (tab) $("sovereign-tab-" + tab)?.click();
  return node;
}

function renderLawsAbilities(parent, owner) {
  const powers = [...lawsRows(owner.capabilities), ...lawsRows(owner.abilities)];
  const seen = new Set();
  let section, missing = false;
  for (const [index, power] of powers.entries()) {
    if (!power || power.known_to_player === false || power.known === false) continue;
    let copy = lawsText(power), name = typeof power === "object" ? power.name || power.title || power.label || "" : "";
    if (!name && typeof power === "string") {
      const split = power.indexOf(":");
      if (split > 0 && split <= 70) { name = power.slice(0, split).trim(); copy = power.slice(split + 1).trim(); }
    }
    const signature = name + "\n" + copy;
    if (seen.has(signature)) continue;
    seen.add(signature);
    if (!copy) { missing = true; continue; }
    if (!section) { section = element("section", undefined, "laws-abilities"); section.append(element("h4", "Abilities")); parent.append(section); }
    if (!name) { renderValue(section, copy); continue; }
    const detail = recordDetail(section, name, owner.id + "-ability-" + (power.id || index));
    detail.classList.add("sovereign-effect");
    if (power.rarity) detail.querySelector("summary").classList.add("rarity-" + String(power.rarity).toUpperCase());
    if (power.appearance || power.visual_description) renderLawsAppearance(detail, power, owner.id + "-ability-look-" + index);
    else if (power.flavor_text) paragraph(detail, power.flavor_text, "ability-flavor");
    renderValue(detail, abilityCopy(copy));
  }
  if (missing) paragraph(parent, "Some ability descriptions haven't been added to this save yet.", "muted");
}

function renderLawsOwner(parent, owner, label, visual = true) {
  if (!owner || owner.known_to_player === false || owner.known === false) return;
  const card = sovereigntyCard(parent, owner.name, label);
  card.dataset.lawsOwner = owner.id;
  if (owner.rarity) card.querySelector("h3").classList.add("rarity-" + owner.rarity);
  if (visual) renderLawsAppearance(card, owner, "appearance-" + owner.id);
  else if (owner.description) paragraph(card, owner.description);
  renderFacts(card, [
    ["Origin", owner.history], ["Deed", owner.deed], ["Known by", owner.recognition],
    ["What it does", owner.effect], ["Objective", owner.objective], ["Outcome", owner.outcome]
  ]);
  renderLawsAbilities(card, owner);
  const upgrades = (owner.upgrades || []).filter(item => item.known_to_player !== false);
  if (upgrades.length) {
    const history = recordDetail(card, "Upgrades · " + upgrades.length, "laws-upgrades-" + owner.id);
    for (const upgrade of upgrades) {
      history.append(element("h4", upgrade.name, "rarity-" + upgrade.rarity));
      renderValue(history, lawsText(upgrade));
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
  $("title-skills").textContent = "Core Powers";
  $("nav-skills").querySelector(".nav-title").textContent = "Core Powers";
  $("hero").textContent = character.name + " · Level " + (character.level || 1) + " · " + character.class_name;
  $("resources").replaceChildren();
  $("characterPreview").textContent = "Level " + (character.level || 1) + " · " + character.rarity + (body ? " · " + body.form : " · Creation");
  $("skillsPreview").textContent = next.abilities.length + " core powers";
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
  paragraph($("character"), "Level " + (character.level || 1), "muted");
  if (body || character.appearance) renderLawsAppearance($("character"), {appearance:character.appearance || body?.appearance || body?.description}, "your-appearance", "Your appearance");
  const nextLevel = next.quest_log.find(quest => quest.system_reward?.level_up && !["completed", "failed", "abandoned"].includes(questStatus(quest)));
  if (nextLevel) paragraph($("character"), "Next level · " + nextLevel.finish_condition, "page-lead");
  if (next.phase !== "adventure" && next.rules_check?.missing?.length) paragraph($("character"), "Still to prepare · " + next.rules_check.missing.join("; "), "muted");
  const policy = {class_offers:12, other_offers:6, picks:2, ...next.creation.selection_policy};
  const growth = recordDetail($("character"), "How your powers grow", "laws-progression-guide");
  renderFacts(growth, [
    ["Your main powers", "Four core powers, shaped by your class and creature."],
    ["Class selection", policy.class_offers + " options · choose one"],
    ["Other selection boards", policy.other_offers + " options · choose " + policy.picks],
    ["Starting upgrades", policy.picks + " core-power upgrades and " + policy.picks + " Sovereign upgrades."],
    ["Each level", "Two core-power upgrades and two Sovereign upgrades when the announced milestone is reached."],
    ["Every fourth level", "Two additional major core-power refinements at levels 4, 8, 12 and beyond."],
    ["Class rarity", "An announced Ascension quest grants the next Class tier and two class-grade refinements."],
    ["Core-power upgrades", "Expand one of your four powers with a new usable possibility."],
    ["Sovereign upgrades", "Give your Domain, General or forces a new capability."],
    ["Origin and Title growth", "Earned through related quests, discoveries and deeds; shown on the identity that grows."]
  ]);
  const owed = new Map();
  const spent = new Map();
  const kitOwners = [...next.abilities, sovereignty.domain, ...sovereignty.commanders, ...sovereignty.formations];
  for (const owner of kitOwners) for (const upgrade of owner.upgrades || []) {
    const kind = next.abilities.includes(owner) ? upgrade.award_kind || "core" : "sovereign";
    const key = upgrade.source + ":" + kind;
    spent.set(key, (spent.get(key) || 0) + 1);
  }
  for (const quest of next.quest_log) {
    const earned = next.quest_settlements?.[quest.id]?.system;
    if (!earned) continue;
    const labels = {core:"Core upgrades",sovereign:"Sovereign upgrades",major:"Major refinements",ascension:"Ascension refinements"};
    const choices = [];
    for (const [kind, label] of Object.entries(labels)) {
      const count = (earned[kind + "_picks"] || 0) - (spent.get("quest:" + quest.id + ":" + kind) || 0);
      if (count > 0) choices.push(label + " · choose " + count);
    }
    if (choices.length) owed.set(quest.name, choices.join("; "));
  }
  if (owed.size) renderFacts(recordDetail($("character"), "Earned choices to make", "laws-earned-choices"), [...owed]);
  const story = recordDetail($("character"), "Your story", "character-story");
  story.className = "character-story";
  const copy = element("div", undefined, "story-copy");
  paragraph(copy, character.story_summary || "Your story takes shape during creation.");
  story.append(copy);
  for (const origin of next.creation.origins || (next.creation.origin ? [next.creation.origin] : [])) renderLawsOwner($("character"), origin, "Origin trait", false);
  for (const title of next.creation.titles || (next.creation.title ? [next.creation.title] : [])) renderLawsOwner($("character"), title, "Title", false);
  renderSkills(next.abilities);
  renderRecords($("health"), next.conditions, "Your current condition is clear.");
  for (const ally of allies) renderLawsOwner($("summons"), ally, sovereignty.commanders.includes(ally) ? "General" : sovereignty.formations.includes(ally) ? "Army & minions" : "Companion");
  for (const enemy of enemies) renderLawsOwner($("summons"), enemy, "Threat");
  if (!allies.length && !enemies.length) paragraph($("summons"), "Your allies and current threats appear here.", "muted");
  for (const item of next.inventory) renderLawsOwner($("equipment"), item, item.holder || item.location || "Gear");
  if (!next.inventory.length) paragraph($("equipment"), "Your acquired gear appears here.", "muted");
  renderQuests($("quests"), next.quest_log);
  const sovereignPanels = lawsSovereigntyPanels($("sovereignty"));
  renderSovereignBody(sovereignPanels.domain, next);
  renderLawsOwner(sovereignPanels.domain, sovereignty.domain, "Domain");
  for (const [key, label] of [["holdings", "Holding"], ["assets", "Asset"], ["encounters", "Encounter"]]) {
    for (const item of sovereignty.domain[key] || []) renderLawsOwner(sovereignPanels.domain, item, label);
  }
  for (const [group, label, panel] of [[sovereignty.commanders, "General", sovereignPanels.commanders], [sovereignty.formations, "Army & minions", sovereignPanels.forces]]) {
    for (const owner of group) renderLawsOwner(panel, owner, owner.side === "enemy" ? "Opposition" : label);
    if (!group.length) paragraph(panel, label === "General" ? "Your General will appear here when one joins you." : "Your army and minions will appear here when established.", "muted");
  }
  for (const [key, label] of [["operations", "Standing orders"], ["fronts", "Current conflict"]]) {
    if (sovereignty[key].length) {
      const activity = recordDetail(sovereignPanels.domain, label, "laws-" + key);
      for (const item of sovereignty[key]) renderLawsOwner(activity, item, label, false);
    }
  }
  renderWorld(next);
  renderCampaignLife(next);
  renderCampaignFocus(next);
  renderChoices();
  restorePreferences();
  updateSaveTools();
  refreshDashboardSearch();
}
