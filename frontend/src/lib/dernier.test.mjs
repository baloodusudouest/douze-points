// Tests de lib/dernier.js : node --test frontend/src/lib/dernier.test.mjs
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { place, plan, pourGagner, premier, RYTHME } from './dernier.js'

const AUTRES = [170, 160, 150, 140, 130, 120, 110, 100, 90, 80]      // le premier : 170

test('place : à égalité, le dernier pays reste sous l\'autre', () => {
  assert.equal(place(171, AUTRES), 1)
  assert.equal(place(170, AUTRES), 2)
  assert.equal(place(93, AUTRES), 9)
  assert.equal(place(10, AUTRES), 11)
})

test('pour gagner : comme la capture (+78 à 93, +32 à 139, +1 à 170)', () => {
  assert.equal(pourGagner(93, 170), 78)
  assert.equal(pourGagner(139, 170), 32)
  assert.equal(pourGagner(170, 170), 1)
  assert.equal(pourGagner(211, 170), 0)
})

test('il dépasse : vite, puis lent sur les places 6 à 2, pause de 2 s à égalité, puis vite jusqu\'au total', () => {
  const p = plan(60, 211, AUTRES)
  assert.equal(p.gagne, true)
  const totaux = p.etapes.map((e) => e.total)
  assert.deepEqual(totaux, [81, 91, 101, 111, 121, 131, 141, 151, 161, 170, 211])
  const egal = p.etapes.find((e) => e.total === 170)
  assert.equal(egal.place, 2)
  assert.equal(egal.pause, RYTHME.pause)
  assert.equal(p.etapes.at(-1).place, 1)
  assert.equal(p.etapes.at(-1).duree, RYTHME.final)
  const vites = p.etapes.slice(0, -1).filter((e) => e.place > 6)
  assert.deepEqual(vites.map((e) => e.place), [10, 9, 8, 7])          // très vite tant qu'il est au-delà de la 6e
  for (const e of p.etapes.slice(0, -1)) {
    assert.equal(e.duree, e.place > 6 ? Math.round(RYTHME.rapide / vites.length) : RYTHME.lent, `place ${e.place}`)
  }
  assert.deepEqual(p.etapes.filter((e) => e.duree === RYTHME.lent).map((e) => e.place), [6, 5, 4, 3, 2, 2])
  assert.equal(p.etapes.filter((e) => e.pause).length, 1)
})

test('il ne dépasse pas : il s\'arrête où il est, sans pause', () => {
  const p = plan(60, 145, AUTRES)
  assert.equal(p.gagne, false)
  assert.equal(p.etapes.at(-1).total, 145)
  assert.equal(p.etapes.at(-1).place, 4)
  assert.equal(p.etapes.filter((e) => e.pause).length, 0)
})

test('égalité exacte avec le premier : il reste 2e, le premier gagne, pas de pause', () => {
  const p = plan(100, 170, AUTRES)
  assert.equal(p.gagne, false)
  assert.equal(p.egalite, true)
  assert.equal(p.etapes.at(-1).total, 170)
  assert.equal(p.etapes.at(-1).place, 2)
  assert.equal(p.etapes.filter((e) => e.pause).length, 0)
})

test('déjà premier avant ce pas : il compte sans monter', () => {
  const p = plan(180, 200, AUTRES)
  assert.equal(p.deja, true)
  assert.deepEqual(p.etapes, [{ total: 200, place: 1, duree: RYTHME.final, pause: 0 }])
})

test('zéro point : aucune étape', () => {
  assert.deepEqual(plan(120, 120, AUTRES).etapes, [])
})

test('une seule chanson : il gagne d\'office', () => {
  const p = plan(0, 12, [])
  assert.equal(p.gagne, true)
  assert.equal(p.etapes.length, 1)
})

test('il part pile au total du premier et le dépasse : pause, puis la fin', () => {
  const p = plan(170, 175, AUTRES)
  assert.deepEqual(p.etapes.map((e) => [e.total, e.pause > 0]), [[170, true], [175, false]])
})

test('beaucoup de pays : les places lointaines passent vite, jamais sous la durée minimale', () => {
  const autres = Array.from({ length: 40 }, (_, i) => 200 - i * 3)
  const p = plan(0, 205, autres)
  const vites = p.etapes.filter((e) => e.place > 6 && e.total !== 205)
  assert.ok(vites.length > 20)
  assert.ok(vites.every((e) => e.duree === RYTHME.minimum))
})

test('premier des autres : le plus haut total, l\'ordre départage', () => {
  assert.equal(premier({ 1: 50, 2: 80, 3: 80, 4: 99 }, 4, [3, 2, 1, 4]), 3)
  assert.equal(premier({ 1: 50, 2: 80, 3: 80, 4: 99 }, 4, [2, 3, 1, 4]), 2)
})

// ---- 1.8.0
import { colonnes, caseDe, placesAutres, avance, dureeEntree } from './dernier.js'

test('colonnes : deux quand les places deviennent trop basses', () => {
  assert.equal(colonnes(14, 600, 30), 1)        // 42 px par place
  assert.equal(colonnes(26, 600, 30), 2)        // 23 px par place
  assert.equal(colonnes(20, 600, 30), 1)        // 30 px tout juste
  assert.equal(colonnes(1, 10, 30), 1)
  assert.equal(colonnes(26, 0, 30), 1)          // pas encore mesuré
})

test('caseDe : moitié haute à gauche, moitié basse à droite', () => {
  assert.deepEqual(caseDe(1, 26, 2), { col: 0, rang: 1, lignes: 13 })
  assert.deepEqual(caseDe(13, 26, 2), { col: 0, rang: 13, lignes: 13 })
  assert.deepEqual(caseDe(14, 26, 2), { col: 1, rang: 1, lignes: 13 })
  assert.deepEqual(caseDe(25, 25, 2), { col: 1, rang: 12, lignes: 13 })   // nombre impair : la gauche a une ligne de plus
  assert.deepEqual(caseDe(7, 14, 1), { col: 0, rang: 7, lignes: 14 })
  assert.deepEqual(caseDe(99, 14, 1), { col: 0, rang: 14, lignes: 14 })
})

test('placesAutres : ceux que le dernier pays a rejoints descendent d\'une place', () => {
  const rangs = ['it', 'fr', 'es', 'no']
  assert.deepEqual(placesAutres(rangs, 5), { it: 1, fr: 2, es: 3, no: 4 })
  assert.deepEqual(placesAutres(rangs, 3), { it: 1, fr: 2, es: 4, no: 5 })
  assert.deepEqual(placesAutres(rangs, 1), { it: 2, fr: 3, es: 4, no: 5 })
})

test('avance : « + 3 points » seulement s\'il passe devant', () => {
  assert.equal(avance(173, 170), 3)
  assert.equal(avance(170, 170), 0)
  assert.equal(avance(150, 170), 0)
})

test('dureeEntree : 120 ms par pays, 2,5 s au plus', () => {
  assert.equal(dureeEntree(13), 1560)
  assert.equal(dureeEntree(40), 2500)
  assert.equal(dureeEntree(0), 0)
})
