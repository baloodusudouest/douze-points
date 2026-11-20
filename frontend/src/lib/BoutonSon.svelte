<script>
  // 1.11.0 : le haut-parleur des écrans de la télé (écran du QR code, dévoilement). Muet gardé par cet écran
  // (localStorage, lib/sons.js) ; coupé, il se voit de loin (haut-parleur barré, fond rose). Quand le navigateur
  // bloque le son (aucun geste depuis le chargement), « Activer le son » s'affiche, avec la vérité sur l'iPhone
  // (avis du conseil 1.11.0). Rien quand les sons sont coupés dans les Réglages.
  import { onDestroy } from 'svelte'
  import Volume2 from '@lucide/svelte/icons/volume-2'
  import VolumeX from '@lucide/svelte/icons/volume-x'
  import { basculerMuet, debloquer, ecouter } from '$lib/sons.js'

  let e = $state({ actifs: true, muet: false, bloque: true })
  const fin = ecouter((x) => (e = x))
  onDestroy(fin)

  function activer(ev) {
    ev.stopPropagation()
    debloquer()
  }
  function basculer(ev) {
    ev.stopPropagation()
    debloquer()
    basculerMuet()
  }
</script>

{#if e.actifs}
  <div class="son pointer-events-auto flex items-start justify-end gap-2">
    {#if e.bloque && !e.muet}
      <div class="activer" role="status">
        <button class="bouton-activer" onclick={activer}>Activer le son</button>
        <p>Le son se réactive d'un toucher après chaque rechargement. Sur iPhone, le bouton silencieux le coupe.</p>
      </div>
    {/if}
    <button class="haut-parleur" class:coupe={e.muet} onclick={basculer} aria-pressed={e.muet}
            aria-label={e.muet ? 'Remettre le son' : 'Couper le son'} title={e.muet ? 'Son coupé : toucher pour le remettre' : 'Couper le son'}>
      {#if e.muet}<VolumeX class="size-5" aria-hidden="true" />{:else}<Volume2 class="size-5" aria-hidden="true" />{/if}
    </button>
  </div>
{/if}

<style>
  .haut-parleur { display: grid; width: 2.75rem; height: 2.75rem; flex-shrink: 0; place-items: center; border-radius: 999px;
    border: 1px solid var(--border); background: var(--background); color: var(--muted-foreground); }
  .haut-parleur.coupe { border-color: var(--primary); background: var(--primary); color: var(--primary-foreground); }
  .haut-parleur:focus-visible, .bouton-activer:focus-visible { outline: 3px solid var(--foreground); outline-offset: 2px; }
  .activer { display: grid; max-width: 17rem; gap: 0.35rem; border-radius: 0.9rem; border: 1px solid var(--border);
    background: color-mix(in oklab, var(--card) 92%, transparent); padding: 0.55rem 0.7rem; text-align: left; }
  .activer p { font-size: 0.72rem; line-height: 1.3; color: var(--muted-foreground); }
  .bouton-activer { min-height: 2.5rem; border-radius: 999px; background: var(--primary); color: var(--primary-foreground);
    padding: 0 1rem; font-size: 0.9rem; font-weight: 600; }
</style>
