// 1.7.0 : le calcul de l'animation du dernier vote du public (télé et téléphones), sans rien d'autre : JS pur,
// testé par `node --test` (tests/test_dernier_js.py le lance). Choix de Julien (19/11/2026) : la carte du dernier pays
// monte l'échelle des places très vite, ralentit pour les 5 dernières places (de la 6e à la 2e), s'arrête 2 secondes
// à « + 1 point pour gagner », puis monte d'un coup jusqu'à son total s'il dépasse le premier.

export const RYTHME = { rapide: 1200, lent: 800, pause: 2000, final: 600, minimum: 60 }

// La place d'un total parmi les autres : à égalité, le dernier pays reste sous l'autre (capture 170 / 170 en 02).
export function place(total, autres) {
  return 1 + autres.filter((t) => t >= total).length
}

// Les points qui manquent pour passer devant le premier (0 : déjà devant).
export function pourGagner(total, tete) {
  return total > tete ? 0 : tete - total + 1
}

// Le plan de la montée : une suite d'étapes { total, place, duree, pause } jouées l'une après l'autre.
// depart : total avant le pas ; arrivee : total après ; autres : totaux des autres chansons (qui ne bougent pas à ce pas).
export function plan(depart, arrivee, autres, r = RYTHME) {
  const tete = autres.length ? Math.max(...autres) : -Infinity
  const res = { depart, arrivee, tete, gagne: arrivee > tete, egalite: arrivee === tete,
                deja: depart > tete, etapes: [] }
  if (arrivee <= depart) return res
  if (res.deja) {                                  // déjà premier avant ce pas : il compte, sans monter
    res.etapes.push({ total: arrivee, place: 1, duree: r.final, pause: 0 })
    return res
  }
  // Les totaux où il change de place : un point au-dessus de chaque autre total dépassé, sous le premier.
  const paliers = [...new Set(autres)].filter((t) => t < tete && t + 1 > depart && t + 1 <= arrivee)
    .map((t) => t + 1).sort((a, b) => a - b)
  const cibles = paliers.map((t) => ({ total: t, egal: false }))
  if (arrivee > tete) {
    if (tete >= depart && tete > (paliers.at(-1) ?? -Infinity)) cibles.push({ total: tete, egal: true })   // « + 1 point »
    cibles.push({ total: arrivee, egal: false, final: true })
  } else if (!cibles.length || cibles.at(-1).total !== arrivee) {
    cibles.push({ total: arrivee, egal: arrivee === tete })
  }
  const vite = cibles.filter((c) => !c.final && place(c.total, autres) > 6).length
  for (const c of cibles) {
    const p = c.final ? 1 : place(c.total, autres)
    let duree
    if (c.final) duree = r.final
    else if (p > 6) duree = Math.max(r.minimum, Math.round(r.rapide / Math.max(1, vite)))
    else duree = r.lent
    res.etapes.push({ total: c.total, place: p, duree, pause: c.egal && arrivee > tete ? r.pause : 0 })
  }
  return res
}

// Le premier des autres : le plus haut total ; à égalité, celui que `ordre` place le plus haut (classement du serveur
// à la télé, ordre de passage sur les téléphones).
export function premier(totaux, dernier, ordre) {
  let meilleur = null
  for (const id of ordre) {
    if (id === dernier) continue
    if (meilleur === null || totaux[id] > totaux[meilleur]) meilleur = id
  }
  return meilleur
}

// ---- 1.8.0 : les pays en lice (choix de Julien du 20/11/2026)

// Les colonnes de l'échelle : une seule tant que chaque place garde au moins `seuil` pixels de haut, sinon deux
// (moitié haute à gauche, moitié basse à droite).
export function colonnes(nb, hauteur, seuil) {
  if (nb <= 1 || !(hauteur > 0)) return 1
  return hauteur / nb >= seuil ? 1 : 2
}

// Où se trouve une place : { col: 0 ou 1, rang: 1… dans sa colonne, lignes: nombre de lignes d'une colonne }.
export function caseDe(placeN, nb, cols = 1) {
  const lignes = cols === 2 ? Math.ceil(nb / 2) : nb
  const p = Math.max(1, Math.min(nb, placeN))
  return p <= lignes ? { col: 0, rang: p, lignes } : { col: 1, rang: p - lignes, lignes }
}

// La place de chacun des autres pays pendant la montée : ils sont rangés une fois pour toutes (`rangs`, du premier
// au dernier) ; ceux qui sont à la place du dernier pays ou au-dessous descendent d'une place.
export function placesAutres(rangs, placeDernier) {
  return Object.fromEntries(rangs.map((id, i) => [id, i + 1 >= placeDernier ? i + 2 : i + 1]))
}

// L'avance du vainqueur quand le dernier pays dépasse le premier (« + 3 points ») ; 0 sinon.
export function avance(arrivee, tete) {
  return arrivee > tete ? arrivee - tete : 0
}

// La durée de l'entrée des drapeaux : 120 ms par pays, 2,5 s au plus (le dernier pays entre après).
export function dureeEntree(nb, pasMs = 120, plafond = 2500) {
  return Math.min(plafond, Math.max(0, nb) * pasMs)
}

// ---- 1.9.0 : la révélation tient dans le temps réglé (choix de Julien du 20/11/2026) : rythme accéléré à proportion,
// pause de 2 s à « + 1 point » gardée. Les pauses ne se compriment pas ; une étape garde au moins `minimum` ms.
export function echelle(lePlan, maxMs, minimum = 30) {
  if (!maxMs || !lePlan.etapes.length) return lePlan
  const pauses = lePlan.etapes.reduce((t, e) => t + e.pause, 0)
  const durees = lePlan.etapes.reduce((t, e) => t + e.duree, 0)
  if (pauses + durees <= maxMs) return lePlan
  const f = Math.max(0, maxMs - pauses) / durees
  return { ...lePlan, etapes: lePlan.etapes.map((e) => ({ ...e, duree: Math.max(minimum, Math.round(e.duree * f)) })) }
}

export function dureePlan(lePlan) {
  return lePlan.etapes.reduce((t, e) => t + e.duree + e.pause, 0)
}

// 1.9.0 : les notes d'un exemple au pas de la soirée (1, 0,5 ou 0,25), pour le mode d'emploi sur la télé
export function notesExemple(cran) {
  const brutes = [12.5, 14, 16.25, 17.5, 15.5]
  return brutes.map((n) => Math.round(n / cran) * cran)
}
