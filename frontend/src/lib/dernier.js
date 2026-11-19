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
