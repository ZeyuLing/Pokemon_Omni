'use strict';
module.exports=({entries,reference,digest,categories})=>{
 const count=fn=>entries.filter(fn).length;
 const counts=Object.fromEntries(categories.map(c=>[c,count(e=>e.category===c)]).filter(([,n])=>n));
 const bonds=entries.filter(e=>e.category==='rocket_bond_candidate');
 const specific=entries.filter(e=>!['base','dynamax','rocket_bond_candidate','source_variant'].includes(e.category));
 const issue=(e,reason)=>({entry_id:e.entry_id,name:e.name_zh_hans,reason});
 const gaps={schema_version:1,checked_at:'2026-09-20',
  bond_version_and_rules:bonds.map(e=>issue(e,'User and author ROMs agree on species records and decoded art; release number, custom learnsets, transition logic and Omni rules remain unverified.')),
  source_variant_rules:entries.filter(e=>e.source_rom_evidence).map(e=>issue(e,'Hash-locked user ROM stats/types/art and active ability IDs extracted; source learnsets, scripts, ability effects, persistence/reversion and Omni battle rules pending.')),
  rom_document_differences:bonds.filter(e=>Object.keys(e.rom_evidence?.document_differences||{}).length).map(e=>({...issue(e,'Display follows the two agreeing ROMs; author document retained for comparison.'),differences:e.rom_evidence.document_differences})),
  source_contradictions:entries.filter(e=>e.source_issues?.length).map(e=>({...issue(e,e.source_issues),reported_total:e.reported_total,computed_total:Object.values(e.stats).reduce((a,b)=>a+b,0)})),
  artwork:specific.filter(e=>!e.art_reference?.variants.front_default).map(e=>issue(e,'Pinned form API has no dedicated front sprite. Optional fallback is not counted as verified art.')),
  missing_artwork:entries.filter(e=>!e.art_reference?.variants.front_default).map(e=>issue(e,'No selected reference image or generated concept is available. See assets/source/bond-concepts/attempts.json for generation outcomes.')),
  original_concepts:entries.filter(e=>e.art_reference?.status==='ai_original_concept').map(e=>issue(e,'Omni original AI concept only; not evidence of official or Rocket Edition appearance, and not final production art.')),
  ability_crosscheck:entries.filter(e=>e.ability_comparison).map(e=>({...issue(e,e.ability_comparison.explanation_zh),...e.ability_comparison})),
  official_identity:specific.filter(e=>!e.identity_evidence).map(e=>issue(e,'Reference dataset identity is present; no manually verified official per-form citation attached.')),
  project_integration:[{scope:'all entries',reason:'World acquisition routes and story gates require world design; they are intentionally unassigned.'},{scope:'all art',reason:'Preview URLs are not distributable GBA graphics; target assets require conversion/creation and provenance review.'}],
  declared_scope:{released_national_numbers:'1–1025',announced_future:'Separate announcement registry, no invented National numbers or stats',ordinary_dynamax:'Gen8 available non-battle-only persistent forms; excludes Mega and Zacian/Zamazenta/Eternatus. Transient battle-state combinations are not auto-generated.',appearance:'63 Alcremie cream/sweet combinations; 28 Unown; 14 Minior shell/core encodings. Shiny/general gender appearance use image variants, Spinda spots are procedural individual data.'}
 };
 const coverage={schema_version:2,content_sha256:digest,entries:entries.length,base_species:count(e=>e.category==='base'),localized_base_species:1025,
  official_named_forms:count(e=>e.identity_evidence),official_named_forms_by_category:Object.fromEntries(categories.map(c=>[c,count(e=>e.category===c&&e.identity_evidence)]).filter(([,n])=>n)),
  reference_browsable:count(e=>!e.research_only),research_only:count(e=>e.research_only),categories:counts,
  source_form_rows:reference.audit.length,source_form_rows_accounted_for:reference.audit.filter(r=>['represented','represented_as_metadata','excluded'].includes(r.status)).length,
  six_stats_available:count(e=>e.stats),six_stats_crosschecked:count(e=>e.stats_crosscheck?.agrees),author_bond_records:bonds.filter(e=>e.stats).length,
  official_species_identity:count(e=>e.category==='base'&&e.species_identity_evidence),
  ability_scope_differences:count(e=>e.ability_comparison?.status==='different_record_scope'),ability_second_source_missing:count(e=>e.ability_comparison?.status==='second_source_missing'),
  front_art_metadata_mapped:count(e=>e.art_reference?.variants.front_default&&e.art_reference.status!=='ai_original_concept'),front_art_head_confirmed:count(e=>e.art_reference?.front_http_status===200),
  original_concept_art:count(e=>e.art_reference?.status==='ai_original_concept'),artwork_presentation_available:count(e=>e.art_reference?.variants.front_default),
  rom_extracted_bond_art:count(e=>e.art_reference?.status==='rom_extracted'),rom_verified_bond_records:count(e=>e.rom_evidence),
  source_rom_variant_records:count(e=>e.source_rom_evidence),source_rom_variant_art:count(e=>e.art_reference?.status==='source_rom_extracted'),
  alcremie_appearance_combinations:count(e=>e.pokeapi?.identifier.startsWith('alcremie-')&&e.pokeapi.identifier!=='alcremie-gmax'),
  limitations:['Reference catalog coverage is complete against the two pinned source inventories, not a claim that every fact is officially certified.','23 bonds have crosschecked ROM records and local front/back art; release number, learnsets and rules remain unverified with disabled registration.','ROM-derived PNGs are local-only and must be regenerated from the pinned inputs on another checkout.','See gaps.json for actual source contradictions.','Announced 2027 identities are separate from released numbered species.','Game world acquisition and final GBA integration remain platform/world work.']
 };
 return {coverage,gaps};
};
