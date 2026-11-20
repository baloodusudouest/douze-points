<script>
  // Le dernier vote du public, joué sur la télé (pages/Devoilement.svelte) et sur les téléphones (invite/Spectacle.svelte)
  // au dernier pas du public, à la place du tableau.
  // 1.7.0 (choix de Julien du 19/11/2026, comme à la finale de l'Eurovision Asia 2026) : au centre l'échelle des places ;
  // à gauche le pays en tête, « En tête » ; à droite le dernier pays, « + X points pour gagner », qui monte l'échelle :
  // très vite, puis lentement de la 6e à la 2e place, 2 secondes d'arrêt à « + 1 point », puis d'un coup jusqu'à son
  // total s'il dépasse le premier. S'il ne passe pas devant : il s'arrête où il est, « + X » disparaît et « Vainqueur »
  // se pose sur le premier.
  // 1.8.0 (choix de Julien du 20/11/2026) : « les pays en lice ». D'abord tous les pays se posent sur l'échelle, un par
  // un ; les autres pays n'ont que leur drapeau (nom et drapeau pour le pays en tête et pour le dernier pays). Puis le
  // dernier pays entre à sa place après le jury et monte. Quand il dépasse : « Vainqueur » et son avance « + 3 points ».
  // Égalité au sommet : « Égalité », le vainqueur est celui du classement de la soirée (`gagnant`). Trop de pays pour la
  // hauteur : l'échelle est coupée en deux (moitié haute à gauche, moitié basse à droite).
  // Les calculs sont dans lib/dernier.js (testés seuls).
  import { onDestroy } from 'svelte'
  import { prefersReducedMotion } from 'svelte/motion'
  import { drapeau } from '$lib/pays.js'
  import Compteur from '$lib/Compteur.svelte'
  import { avance, caseDe, colonnes, dureeEntree, echelle, place, placesAutres, plan, pourGagner, premier, RYTHME } from '$lib/dernier.js'

  // chansons : [{ id, pays, code_pays, ordre }] ; totaux : { id: total après ce pas } ; dernier : l'id du dernier pays ;
  // gain : ses points à ce pas ; ordre : ids pour départager une égalité ; gagnant : le vainqueur du classement de la
  // soirée (facultatif) ; anime : false = état final direct (rechargement, téléphone arrivé en retard, Revenir) ;
  // compact : téléphone en portrait ; rythme : accéléré par les tests (window.__DOUZE_POINTS_RYTHME, jamais en soirée).
  // 1.9.0 : maxMs = la durée maximum de la remontée (Réglages › Dévoilement, « Révélation ») : rythme accéléré à
  // proportion, pause de 2 s gardée ; onfini() est appelé une fois l'animation jouée (la télé enchaîne sur le podium).
  let { chansons, totaux, dernier, gain, ordre, gagnant = null, anime = true, compact = false, maxMs = 0,
        onfini = () => {},
        rythme = (typeof window !== 'undefined' && window.__DOUZE_POINTS_RYTHME) || RYTHME } = $props()

  const parId = $derived(Object.fromEntries(chansons.map((c) => [c.id, c])))
  const autres = $derived(chansons.filter((c) => c.id !== dernier).map((c) => totaux[c.id]))
  const tete = $derived(premier(totaux, dernier, ordre))
  const depart = $derived(totaux[dernier] - gain)
  const arrivee = $derived(totaux[dernier])
  const le_plan = $derived(echelle(plan(depart, arrivee, autres, rythme), maxMs))
  const nb = $derived(chansons.length)
  // Les autres pays, du premier au dernier (à égalité, l'ordre du classement)
  const rangs = $derived.by(() => {
    const i = Object.fromEntries(ordre.map((id, k) => [id, k]))
    return chansons.filter((c) => c.id !== dernier).map((c) => c.id)
      .sort((a, b) => totaux[b] - totaux[a] || (i[a] ?? 0) - (i[b] ?? 0))
  })
  const egalite = $derived(tete !== null && arrivee === totaux[tete])
  const vainqueurFinal = $derived(gagnant ?? (le_plan.gagne || le_plan.deja ? dernier : tete))

  // ---- le déroulé : entrée des drapeaux, puis un seul nombre animé (le total affiché du dernier pays)
  let phase = $state('entree')    // entree → montee → fin
  let affiche = $state(0)         // total affiché
  let duree = $state(0)           // durée du compteur pour l'étape en cours
  let minuteur
  let lance = false
  const vite = (rythme.rapide ?? RYTHME.rapide) / RYTHME.rapide          // les tests accélèrent aussi l'entrée
  const pasEntree = $derived(nb > 1 ? Math.round(dureeEntree(nb - 1, 120 * vite, 2500 * vite) / (nb - 1)) : 0)

  function jouer(i) {
    if (i >= le_plan.etapes.length) { phase = 'fin'; onfini(); return }
    const e = le_plan.etapes[i]
    duree = e.duree
    affiche = e.total
    minuteur = setTimeout(() => jouer(i + 1), e.duree + e.pause)
  }
  $effect(() => {
    if (lance) return
    lance = true
    if (!anime || prefersReducedMotion.current) {
      duree = 0; affiche = arrivee; phase = 'fin'
      if (anime) onfini()
      return
    }
    affiche = depart; duree = 0; phase = 'entree'
    const entree = dureeEntree(nb - 1, 120 * vite, 2500 * vite) + Math.round(500 * vite)
    minuteur = setTimeout(() => {
      phase = 'montee'
      if (!le_plan.etapes.length) { minuteur = setTimeout(() => { phase = 'fin'; onfini() }, Math.round(900 * vite)); return }
      minuteur = setTimeout(() => jouer(0), Math.round(900 * vite))     // le temps de voir le point de départ
    }, entree)
  })
  onDestroy(() => clearTimeout(minuteur))

  const termine = $derived(phase === 'fin')
  const entree = $derived(phase === 'entree')
  const placeDernier = $derived(entree ? nb + 1 : termine ? (vainqueurFinal === dernier ? 1 : place(arrivee, autres))
    : (le_plan.deja ? 1 : place(affiche, autres)))
  const placeDe = $derived(placesAutres(rangs, placeDernier))
  const manque = $derived(pourGagner(affiche, tete === null ? -Infinity : totaux[tete]))
  const vainqueur = $derived(termine ? vainqueurFinal : null)
  const ecart = $derived(tete === null ? 0 : avance(arrivee, totaux[tete]))

  // ---- la mise en page : une ou deux colonnes selon la hauteur disponible
  let hauteur = $state(0)
  const cols = $derived(colonnes(nb, hauteur, compact ? 22 : 30))
  const lignes = $derived(cols === 2 ? Math.ceil(nb / 2) : nb)
  const caseP = (p) => caseDe(p, nb, cols)
  const haut = (p) => { const k = caseP(p); return `${((k.rang - 0.5) / k.lignes) * 100}%` }
  const echelleA = $derived(Array.from({ length: lignes }, (_, i) => i + 1))
  const echelleB = $derived(cols === 2 ? Array.from({ length: nb - lignes }, (_, i) => lignes + i + 1) : [])
  const prise = (p) => (!entree && p === placeDernier) || (tete !== null && p === placeDe[tete])
  const numero = (p) => String(p).padStart(2, '0')
  // les drapeaux des autres pays (ni le pays en tête ni le dernier), avec leur ordre d'entrée
  const drapeaux = $derived(rangs.slice(1).map((id, k) => ({ id, c: parId[id], place: placeDe[id], retard: (k + 1) * pasEntree })))
  const dernierCol = $derived(caseP(Math.min(placeDernier, nb)).col)

  const COULEURS = ['#e5559f', '#f2ece2', '#a98fd8', '#ffd84d', '#7f9cc4', '#8fae6b']
  const cotillons = Array.from({ length: compact ? 45 : 90 }, (_, i) => ({
    gauche: Math.random() * 100, retard: Math.random() * 1.8, duree: 2.6 + Math.random() * 2.4, couleur: COULEURS[i % COULEURS.length],
    largeur: 5 + Math.random() * 6, tourne: Math.random() * 360, rond: i % 4 === 0,
  }))
</script>

<div class="dernier" class:compact class:deux={cols === 2} role="group" aria-label="Le dernier vote du public">
  <p class="titre">{entree ? 'Les pays en lice' : 'Le dernier vote du public'}</p>
  <div class="scene" bind:clientHeight={hauteur}>
    <!-- colonne de gauche : le pays en tête et les drapeaux de la moitié haute (ou de tous, en une colonne) -->
    <div class="cote gauche">
      {#each drapeaux.filter((f) => caseP(f.place).col === 0) as f (f.id)}
        <span class="drapeau-seul" class:entre={anime} style="top: {haut(f.place)}; animation-delay: {f.retard}ms"
              title="{f.c.pays}, {f.place}e" aria-hidden="true">{drapeau(f.c.pays, f.c.code_pays)}</span>
      {/each}
      {#if tete !== null}
        {@const c = parId[tete]}
        <div class="carte tete" style="top: {haut(placeDe[tete])}">
          {#if vainqueur === tete}<span class="etiquette vainqueur">Vainqueur</span>
          {:else if placeDe[tete] === 1 && !termine}<span class="etiquette tete">En tête</span>{/if}
          <span class="nom">{c.pays}</span><span class="drap">{drapeau(c.pays, c.code_pays)}</span><span class="points chiffre">{totaux[tete]}</span>
        </div>
      {/if}
    </div>

    <ol class="echelle" aria-hidden="true">
      {#each echelleA as p}<li class:prise={prise(p)}>{numero(p)}</li>{/each}
    </ol>

    <!-- le dernier pays : à droite de l'échelle (ou entre les deux échelles) -->
    <div class="cote droite" class:vers-b={cols === 2 && dernierCol === 1}>
      {#if parId[dernier] && !entree}
        {@const c = parId[dernier]}
        <div class="carte dernier-pays" class:vient={anime} style="top: {haut(Math.min(placeDernier, nb))}">
          {#if vainqueur === dernier}
            <span class="etiquettes"><span class="etiquette vainqueur">Vainqueur</span>{#if ecart > 0}<span class="etiquette manque">+ {ecart} {ecart > 1 ? 'points' : 'point'}</span>{/if}</span>
          {:else if termine && egalite}<span class="etiquettes"><span class="etiquette manque">Égalité</span></span>
          {:else if !termine && manque > 0}<span class="etiquettes"><span class="etiquette manque">+ {manque} {compact ? 'pts' : manque > 1 ? 'points' : 'point'} pour gagner</span></span>{/if}
          <span class="points chiffre"><Compteur valeur={affiche} depart={depart} {duree} /></span><span class="drap">{drapeau(c.pays, c.code_pays)}</span><span class="nom">{c.pays}</span>
        </div>
      {/if}
    </div>

    {#if cols === 2}
      <ol class="echelle" aria-hidden="true">
        {#each echelleB as p}<li class:prise={prise(p)}>{numero(p)}</li>{/each}
      </ol>
      <div class="cote droite-b">
        {#each drapeaux.filter((f) => caseP(f.place).col === 1) as f (f.id)}
          <span class="drapeau-seul" class:entre={anime} style="top: {haut(f.place)}; animation-delay: {f.retard}ms"
                title="{f.c.pays}, {f.place}e" aria-hidden="true">{drapeau(f.c.pays, f.c.code_pays)}</span>
        {/each}
      </div>
    {/if}
  </div>

  {#if termine && vainqueur !== null}
    <p class="sr-only" aria-live="polite">Vainqueur : {parId[vainqueur].pays}, {totaux[vainqueur]} points{vainqueur === dernier && ecart ? `, ${ecart} points d'avance` : ''}.</p>
    {#if !prefersReducedMotion.current}
      <div class="cotillons" aria-hidden="true">
        {#each cotillons as k}
          <i style="left: {k.gauche}%; width: {k.largeur}px; height: {k.rond ? k.largeur : k.largeur * 1.8}px; background: {k.couleur}; border-radius: {k.rond ? '50%' : '1px'}; animation-duration: {k.duree}s; animation-delay: {k.retard}s; --tourne: {k.tourne}deg"></i>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .dernier { --jaune: #ffd84d; --carte: #f6f0ff; --encre: #1b1035; --echelle-l: clamp(2.8rem, 6vw, 4.5rem);
    position: relative; display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; padding: 0.4rem 0.5rem 0.8rem; }
  .compact { --echelle-l: 2.3rem; padding: 0.2rem 0.1rem 0.4rem; }
  .titre { margin: 0 0 0.3rem; text-align: center; font-size: clamp(0.95rem, 3.2vh, 1.4rem); font-weight: 300; color: var(--primary); }
  .scene { position: relative; display: grid; flex: 1; min-height: 0; padding-top: 1.8rem;
    grid-template-columns: minmax(0, 1fr) var(--echelle-l) minmax(0, 1fr); gap: clamp(0.4rem, 1.5vw, 1.2rem); }
  .compact .scene { gap: 0.3rem; padding-top: 1.6rem; }
  .deux .scene { grid-template-columns: minmax(0, 0.8fr) var(--echelle-l) minmax(0, 1.4fr) var(--echelle-l) minmax(0, 0.8fr); }
  .echelle { display: flex; flex-direction: column; border-radius: 999px; padding: 0.35rem 0;
    background: linear-gradient(180deg, #e5559f, #8f6ad8 70%, #5b3fb0); box-shadow: 0 0 2.5rem rgba(229, 85, 159, 0.25); }
  .echelle li { display: grid; flex: 1; min-height: 0; place-items: center; color: rgba(255, 255, 255, 0.92); font-weight: 700;
    font-size: clamp(0.5rem, min(2.2vh, 1.6vw), 1.05rem); font-variant-numeric: tabular-nums; }
  .compact .echelle li { font-size: clamp(0.5rem, 1.8vh, 0.8rem); }
  .echelle li.prise { position: relative; }
  .echelle li.prise::after { content: ''; position: absolute; inset: 8% 14%; border: 2px solid #fff; border-radius: 999px; }
  .cote { position: relative; min-width: 0; }
  .carte { position: absolute; display: flex; align-items: center; max-width: 100%; height: clamp(1.9rem, 6.5vh, 3.4rem);
    transform: translateY(-50%); border-radius: 999px; background: var(--carte); color: var(--encre); font-weight: 700;
    font-size: clamp(0.75rem, 2.6vh, 1.5rem); box-shadow: 0 0.4rem 1.4rem rgba(0, 0, 0, 0.35); transition: top 0.32s cubic-bezier(0.3, 0.7, 0.3, 1), left 0.4s, right 0.4s; z-index: 2; }
  .compact .carte { height: 2rem; font-size: 0.78rem; }
  .deux .carte { height: clamp(1.7rem, 5vh, 2.8rem); }
  .gauche .carte { right: 0; padding-left: 0.9em; }
  .droite .carte { left: 0; padding-right: 0.9em; }
  /* en deux colonnes, la carte du dernier pays se colle à l'échelle de droite quand sa place y est */
  .droite.vers-b .carte { left: auto; right: 0; }
  .carte .nom { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 0.6em; }
  .carte .drap { flex-shrink: 0; font-size: 1.35em; line-height: 1; }
  .carte .points { display: grid; flex-shrink: 0; height: 100%; min-width: 2.7em; place-items: center; padding: 0 0.5em; background: var(--jaune);
    font-size: 1.15em; font-variant-numeric: tabular-nums; }
  .gauche .carte .points { border-radius: 0 999px 999px 0; margin-left: 0.4em; }
  .droite .carte .points { border-radius: 999px 0 0 999px; margin-right: 0.4em; }
  .etiquettes { position: absolute; bottom: calc(100% + 0.25rem); left: 1.5em; display: flex; gap: 0.35em; white-space: nowrap; }
  .droite.vers-b .etiquettes { left: auto; right: 1.5em; }
  .etiquette { border-radius: 999px; padding: 0.1em 0.8em; font-size: 0.72em; font-weight: 700; letter-spacing: 0.04em; }
  .gauche .etiquette { position: absolute; bottom: calc(100% + 0.25rem); right: 1.5em; white-space: nowrap; }
  .etiquette.tete, .etiquette.vainqueur { background: #e5559f; color: #fff; }
  .etiquette.vainqueur { animation: briller 1.2s ease-in-out infinite alternate; }
  .etiquette.manque { background: var(--jaune); color: var(--encre); }
  /* les autres pays : le drapeau seul, posé contre l'échelle */
  .drapeau-seul { position: absolute; display: grid; place-items: center; width: clamp(1.5rem, 4.6vh, 2.5rem); aspect-ratio: 1;
    transform: translateY(-50%); border-radius: 999px; background: var(--muted); border: 1px solid var(--border);
    font-size: clamp(0.85rem, 2.6vh, 1.4rem); line-height: 1; transition: top 0.32s cubic-bezier(0.3, 0.7, 0.3, 1); }
  .deux .drapeau-seul { width: clamp(1.3rem, 3.4vh, 2rem); font-size: clamp(0.75rem, 2vh, 1.1rem); }
  .gauche .drapeau-seul { right: 0; }
  .droite-b .drapeau-seul { left: 0; }
  .drapeau-seul.entre { animation: entrer 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .droite-b .drapeau-seul.entre { animation-name: entrer-b; }
  @keyframes entrer { from { opacity: 0; transform: translate(-3rem, -50%) scale(0.5); } to { opacity: 1; transform: translate(0, -50%); } }
  @keyframes entrer-b { from { opacity: 0; transform: translate(3rem, -50%) scale(0.5); } to { opacity: 1; transform: translate(0, -50%); } }
  .carte.vient { animation: venir 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  @keyframes venir { from { opacity: 0; transform: translate(3rem, -50%); } to { opacity: 1; transform: translate(0, -50%); } }
  @keyframes briller { from { box-shadow: 0 0 0 rgba(229, 85, 159, 0); } to { box-shadow: 0 0 1.2rem rgba(229, 85, 159, 0.9); } }
  .cotillons { pointer-events: none; position: absolute; inset: 0; overflow: hidden; }
  .cotillons i { position: absolute; top: -4vh; opacity: 0; animation: tomber linear infinite; }
  @keyframes tomber { 0% { opacity: 1; transform: translateY(0) rotate(var(--tourne)); } 100% { opacity: 1; transform: translateY(108vh) rotate(calc(var(--tourne) + 540deg)); } }
  @media (prefers-reduced-motion: reduce) { .carte, .drapeau-seul { transition: none; } .etiquette.vainqueur, .drapeau-seul.entre, .carte.vient { animation: none; } }
</style>
