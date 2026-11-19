<script>
  // 1.7.0 : l'animation du dernier vote du public, comme à la finale de l'Eurovision Asia 2026 (choix de Julien du
  // 19/11/2026). Jouée sur la télé (pages/Devoilement.svelte) et sur les téléphones (invite/Spectacle.svelte), au dernier
  // pas du public, à la place du tableau. Au centre l'échelle des places ; à gauche le pays en tête, « En tête » ;
  // à droite le dernier pays, « + X points pour gagner », qui monte l'échelle : très vite, puis lentement de la 6e à la
  // 2e place, 2 secondes d'arrêt à « + 1 point », puis d'un coup jusqu'à son total s'il dépasse le premier.
  // S'il ne passe pas devant : il s'arrête où il est, « + X » disparaît et « Vainqueur » se pose sur le premier.
  // Le calcul est dans lib/dernier.js (testé seul).
  import { onDestroy } from 'svelte'
  import { prefersReducedMotion } from 'svelte/motion'
  import { drapeau } from '$lib/pays.js'
  import Compteur from '$lib/Compteur.svelte'
  import { place, plan, pourGagner, premier, RYTHME } from '$lib/dernier.js'

  // chansons : [{ id, pays, code_pays, ordre }] ; totaux : { id: total après ce pas } ; dernier : l'id du dernier pays ;
  // gain : ses points à ce pas ; ordre : ids pour départager une égalité au sommet ; anime : false = état final direct
  // (rechargement, téléphone arrivé en retard, Revenir) ; compact : téléphone en portrait ; rythme : accéléré par les tests.
  // Les tests d'écran accélèrent le rythme par window.__DOUZE_POINTS_RYTHME (jamais posé en soirée).
  let { chansons, totaux, dernier, gain, ordre, anime = true, compact = false,
        rythme = (typeof window !== 'undefined' && window.__DOUZE_POINTS_RYTHME) || RYTHME } = $props()

  const parId = $derived(Object.fromEntries(chansons.map((c) => [c.id, c])))
  const autres = $derived(chansons.filter((c) => c.id !== dernier).map((c) => totaux[c.id]))
  const tete = $derived(premier(totaux, dernier, ordre))
  const depart = $derived(totaux[dernier] - gain)
  const le_plan = $derived(plan(depart, totaux[dernier], autres, rythme))
  const nb = $derived(chansons.length)

  // ---- le déroulé : un seul nombre animé (le total affiché du dernier pays), le reste en découle
  let affiche = $state(0)        // total affiché
  let duree = $state(0)          // durée du compteur pour l'étape en cours
  let termine = $state(false)
  let minuteur
  let lance = false

  function jouer(i) {
    if (i >= le_plan.etapes.length) { termine = true; return }
    const e = le_plan.etapes[i]
    duree = e.duree
    affiche = e.total
    minuteur = setTimeout(() => jouer(i + 1), e.duree + e.pause)
  }
  $effect(() => {
    if (lance) return
    lance = true
    if (!anime || prefersReducedMotion.current || !le_plan.etapes.length) {
      duree = 0
      affiche = totaux[dernier]
      termine = true
    } else {
      affiche = depart
      duree = 0
      minuteur = setTimeout(() => jouer(0), 700)        // le temps de voir le point de départ
    }
  })
  onDestroy(() => clearTimeout(minuteur))

  const placeDernier = $derived(termine && le_plan.gagne ? 1 : (le_plan.deja ? 1 : place(affiche, autres)))
  const placeTete = $derived(placeDernier === 1 && tete !== null ? 2 : 1)
  const manque = $derived(pourGagner(affiche, tete === null ? -Infinity : totaux[tete]))
  const vainqueur = $derived(termine ? (le_plan.gagne || le_plan.deja ? dernier : tete) : null)
  // haut d'une carte, en % de l'échelle : au milieu de sa pastille
  const haut = (p) => `${((p - 0.5) / nb) * 100}%`

  const COULEURS = ['#e5559f', '#f2ece2', '#a98fd8', '#ffd84d', '#7f9cc4', '#8fae6b']
  const cotillons = Array.from({ length: compact ? 45 : 90 }, (_, i) => ({
    gauche: Math.random() * 100, retard: Math.random() * 1.8, duree: 2.6 + Math.random() * 2.4, couleur: COULEURS[i % COULEURS.length],
    largeur: 5 + Math.random() * 6, tourne: Math.random() * 360, rond: i % 4 === 0,
  }))
</script>

<div class="dernier" class:compact role="group" aria-label="Le dernier vote du public">
  <div class="cote gauche">
    {#if tete !== null}
      {@const c = parId[tete]}
      <div class="carte tete" style="top: {haut(placeTete)}">
        {#if vainqueur === tete}<span class="etiquette vainqueur">Vainqueur</span>
        {:else if placeTete === 1}<span class="etiquette tete">En tête</span>{/if}
        <span class="nom">{c.pays}</span><span class="drap">{drapeau(c.pays, c.code_pays)}</span><span class="points chiffre">{totaux[tete]}</span>
      </div>
    {/if}
  </div>

  <ol class="echelle" aria-hidden="true">
    {#each Array.from({ length: nb }, (_, i) => i + 1) as p}
      <li class:prise={p === placeDernier || (tete !== null && p === placeTete)}>{String(p).padStart(2, '0')}</li>
    {/each}
  </ol>

  <div class="cote droite">
    {#if parId[dernier]}
    {@const c = parId[dernier]}
    <div class="carte dernier-pays" style="top: {haut(placeDernier)}">
      {#if vainqueur === dernier}<span class="etiquette vainqueur">Vainqueur</span>
      {:else if !termine && manque > 0}<span class="etiquette manque">+ {manque} {compact ? 'pts' : manque > 1 ? 'points' : 'point'} pour gagner</span>{/if}
      <span class="points chiffre"><Compteur valeur={affiche} depart={depart} {duree} /></span><span class="drap">{drapeau(c.pays, c.code_pays)}</span><span class="nom">{c.pays}</span>
    </div>
    {/if}
  </div>

  {#if termine && vainqueur !== null}
    <p class="sr-only" aria-live="polite">Vainqueur : {parId[vainqueur].pays}, {totaux[vainqueur]} points.</p>
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
    position: relative; display: grid; grid-template-columns: minmax(0, 1fr) var(--echelle-l) minmax(0, 1fr); gap: clamp(0.4rem, 1.5vw, 1.2rem);
    height: 100%; min-height: 0; overflow: hidden; padding: 2.2rem 0.5rem 0.8rem; }
  .compact { --echelle-l: 2.3rem; gap: 0.3rem; padding: 1.8rem 0.1rem 0.4rem; }
  .echelle { display: flex; flex-direction: column; border-radius: 999px; padding: 0.35rem 0;
    background: linear-gradient(180deg, #e5559f, #8f6ad8 70%, #5b3fb0); box-shadow: 0 0 2.5rem rgba(229, 85, 159, 0.25); }
  .echelle li { display: grid; flex: 1; min-height: 0; place-items: center; color: rgba(255, 255, 255, 0.92); font-weight: 700;
    font-size: clamp(0.55rem, min(2.2vh, 1.6vw), 1.05rem); font-variant-numeric: tabular-nums; }
  .compact .echelle li { font-size: clamp(0.5rem, 1.8vh, 0.8rem); }
  .echelle li.prise { position: relative; }
  .echelle li.prise::after { content: ''; position: absolute; inset: 8% 14%; border: 2px solid #fff; border-radius: 999px; }
  .cote { position: relative; min-width: 0; }
  .carte { position: absolute; display: flex; align-items: center; max-width: 100%; height: clamp(1.9rem, 6.5vh, 3.4rem);
    transform: translateY(-50%); border-radius: 999px; background: var(--carte); color: var(--encre); font-weight: 700;
    font-size: clamp(0.75rem, 2.6vh, 1.5rem); box-shadow: 0 0.4rem 1.4rem rgba(0, 0, 0, 0.35); transition: top 0.32s cubic-bezier(0.3, 0.7, 0.3, 1); }
  .compact .carte { height: 2rem; font-size: 0.78rem; }
  .gauche .carte { right: 0; padding-left: 0.9em; }
  .droite .carte { left: 0; padding-right: 0.9em; }
  .carte .nom { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; padding: 0 0.6em; }
  .carte .drap { flex-shrink: 0; font-size: 1.35em; line-height: 1; }
  .carte .points { display: grid; flex-shrink: 0; height: 100%; min-width: 2.7em; place-items: center; padding: 0 0.5em; background: var(--jaune);
    font-size: 1.15em; font-variant-numeric: tabular-nums; }
  .gauche .carte .points { border-radius: 0 999px 999px 0; margin-left: 0.4em; }
  .droite .carte .points { border-radius: 999px 0 0 999px; margin-right: 0.4em; }
  .etiquette { position: absolute; bottom: calc(100% + 0.25rem); white-space: nowrap; border-radius: 999px; padding: 0.1em 0.8em;
    font-size: 0.72em; font-weight: 700; letter-spacing: 0.04em; }
  .gauche .etiquette { right: 1.5em; }
  .droite .etiquette { left: 1.5em; }
  .etiquette.tete, .etiquette.vainqueur { background: #e5559f; color: #fff; }
  .etiquette.vainqueur { animation: briller 1.2s ease-in-out infinite alternate; }
  .etiquette.manque { background: var(--jaune); color: var(--encre); }
  @keyframes briller { from { box-shadow: 0 0 0 rgba(229, 85, 159, 0); } to { box-shadow: 0 0 1.2rem rgba(229, 85, 159, 0.9); } }
  .cotillons { pointer-events: none; position: absolute; inset: 0; overflow: hidden; }
  .cotillons i { position: absolute; top: -4vh; opacity: 0; animation: tomber linear infinite; }
  @keyframes tomber { 0% { opacity: 1; transform: translateY(0) rotate(var(--tourne)); } 100% { opacity: 1; transform: translateY(108vh) rotate(calc(var(--tourne) + 540deg)); } }
  @media (prefers-reduced-motion: reduce) { .carte { transition: none; } .etiquette.vainqueur { animation: none; } }
</style>
