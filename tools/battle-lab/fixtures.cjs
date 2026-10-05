'use strict';
// Authored synthetic integration fixtures, not expert builds or a held-out benchmark.
const set = (species, ability, moves, physical = false, item = 'Leftovers') => ({
  species, ability, moves, item, level: 100, nature: physical ? 'Adamant' : 'Modest',
  evs: physical ? {atk: 252, spe: 252, hp: 4} : {spa: 252, spe: 252, hp: 4},
});
const teams = [
  {id: 'synthetic-balanced', team: [
    set('Infernape', 'Blaze', ['Flamethrower', 'Grass Knot', 'Focus Blast', 'U-turn']),
    set('Starmie', 'Natural Cure', ['Surf', 'Thunderbolt', 'Ice Beam', 'Recover']),
    set('Scizor', 'Technician', ['Bullet Punch', 'U-turn', 'Superpower', 'Swords Dance'], true),
    set('Gengar', 'Levitate', ['Shadow Ball', 'Thunderbolt', 'Focus Blast', 'Substitute']),
    set('Gliscor', 'Hyper Cutter', ['Earthquake', 'Stone Edge', 'Roost', 'Swords Dance'], true),
    set('Blissey', 'Natural Cure', ['Flamethrower', 'Ice Beam', 'Soft-Boiled', 'Thunder Wave']),
  ]},
  {id: 'synthetic-sand', team: [
    set('Tyranitar', 'Sand Stream', ['Crunch', 'Stone Edge', 'Earthquake', 'Dragon Dance'], true),
    set('Swampert', 'Torrent', ['Earthquake', 'Waterfall', 'Ice Punch', 'Stealth Rock'], true),
    set('Magnezone', 'Magnet Pull', ['Thunderbolt', 'Flash Cannon', 'Substitute', 'Thunder Wave']),
    set('Breloom', 'Poison Heal', ['Seed Bomb', 'Mach Punch', 'Substitute', 'Swords Dance'], true, 'Toxic Orb'),
    set('Dragonite', 'Inner Focus', ['Dragon Claw', 'Fire Punch', 'Extreme Speed', 'Dragon Dance'], true),
    set('Vaporeon', 'Water Absorb', ['Surf', 'Ice Beam', 'Protect', 'Wish']),
  ]},
  {id: 'synthetic-offense', team: [
    set('Azelf', 'Levitate', ['Psychic', 'Flamethrower', 'Thunderbolt', 'Stealth Rock']),
    set('Gyarados', 'Intimidate', ['Waterfall', 'Ice Fang', 'Earthquake', 'Dragon Dance'], true),
    set('Lucario', 'Inner Focus', ['Close Combat', 'Extreme Speed', 'Crunch', 'Swords Dance'], true),
    set('Jolteon', 'Volt Absorb', ['Thunderbolt', 'Shadow Ball', 'Signal Beam', 'Thunder Wave']),
    set('Flygon', 'Levitate', ['Earthquake', 'Dragon Claw', 'U-turn', 'Fire Punch'], true),
    set('Heatran', 'Flash Fire', ['Flamethrower', 'Earth Power', 'Dragon Pulse', 'Substitute']),
  ]},
];
module.exports = {teams};
