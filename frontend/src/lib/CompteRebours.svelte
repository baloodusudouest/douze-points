<script>
  // 1.11.0 : le compte à rebours avant la remontée du dernier pays, sur la télé (visuel « 8b », choix de Julien du
  // 20/11/2026). 5 → 0, une seconde par chiffre : un cadre blanc (bordure 10 px) part des bords de l'écran et se
  // resserre jusqu'à la moitié de l'écran en 0,5 s (coins arrondis jusqu'à 28 px, adoucissement cubique), puis
  // s'efface pendant que le grand chiffre fin (Inter 200, halo rose) apparaît en léger zoom arrière (1,08 → 1), tient,
  // puis s'efface de 0,88 à 1 s. Mouvement réduit : les chiffres seuls, sans cadre, toujours 6 s.
  // Calé sur l'heure du serveur (avis du conseil) : `debut` est l'heure de départ du compte sur cette horloge (d'après
  // `pas_le`) ; une télé rechargée pendant le compte reprend au bon chiffre. `onfin` est appelé une fois, à la fin.
  import { onMount, onDestroy } from 'svelte'
  import { prefersReducedMotion } from 'svelte/motion'

  let { debut, duree = 6000, onfin = () => {} } = $props()

  const chiffreA = (ecoule) => Math.max(0, 5 - Math.floor(ecoule / 1000))
  const ecoule = () => Date.now() - debut
  let chiffre = $state(chiffreA(ecoule()))
  // décalage dans la seconde en cours au moment où le chiffre est apparu (reprise au milieu d'un chiffre)
  let decalage = $state(Math.max(0, ecoule() % 1000))
  let fini = false
  let image

  function tic() {
    const e = ecoule()
    if (e >= duree) {
      if (!fini) { fini = true; onfin() }
      return
    }
    const c = chiffreA(e)
    if (c !== chiffre) { decalage = Math.max(0, e - (5 - c) * 1000); chiffre = c }
    image = requestAnimationFrame(tic)
  }
  onMount(() => { image = requestAnimationFrame(tic) })
  onDestroy(() => cancelAnimationFrame(image))
</script>

<div class="compte" class:reduit={prefersReducedMotion.current} role="timer" aria-label="La révélation dans {chiffre} secondes">
  <p class="annonce">La révélation dans…</p>
  {#key chiffre}
    {#if !prefersReducedMotion.current}<div class="cadre" aria-hidden="true" style="animation-delay: -{decalage}ms"></div>{/if}
    <p class="grand" aria-hidden="true" style="animation-delay: -{decalage}ms">{chiffre}</p>
  {/key}
</div>

<style>
  .compte { position: fixed; inset: 0; z-index: 45; display: grid; place-items: center; overflow: hidden; background: var(--background); }
  /* au-dessus du cadre resserré (qui s'arrête à 25 % de la hauteur), sous les commandes de la télé */
  .annonce { position: absolute; top: max(3.6rem, calc(25% - 2.3em)); left: 0; right: 0; text-align: center; font-size: clamp(1rem, 4.2vh, 1.8rem);
    font-weight: 300; letter-spacing: 0.02em; color: var(--muted-foreground); }
  .cadre { position: absolute; box-sizing: border-box; border: 10px solid #fff; animation: resserrer 1s both; }
  @keyframes resserrer {
    0% { inset: 0; border-radius: 0; opacity: 1; animation-timing-function: cubic-bezier(0.65, 0, 0.35, 1); }
    50% { inset: 25%; border-radius: 28px; opacity: 1; animation-timing-function: ease-out; }
    70%, 100% { inset: 25%; border-radius: 28px; opacity: 0; }
  }
  .grand { position: relative; margin: 0; font-family: var(--font-sans); font-weight: 200; font-size: min(46vh, 40vw); line-height: 1;
    font-variant-numeric: tabular-nums; color: #fff;
    text-shadow: 0 0 0.12em color-mix(in oklab, var(--app) 85%, transparent), 0 0 0.4em color-mix(in oklab, var(--app) 55%, transparent);
    animation: chiffre 1s both; }
  @keyframes chiffre {
    0%, 50% { opacity: 0; transform: scale(1.08); animation-timing-function: cubic-bezier(0.2, 0.8, 0.2, 1); }
    68% { opacity: 1; transform: scale(1); }
    88% { opacity: 1; transform: scale(1); }
    100% { opacity: 0; transform: scale(1); }
  }
  .reduit .grand { animation: none; opacity: 1; transform: none; }
</style>
