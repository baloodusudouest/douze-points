<script>
  // 1.13 : le « ? » à côté du collage de la liste : un prompt prêt à coller dans une IA (ChatGPT, Claude…) pour
  // obtenir la liste des chansons au bon format, avec les vrais votes si le concours a déjà eu lieu.
  // Le presse-papiers moderne exige une page sûre (https) : en http sur le Wi-Fi, on passe par une zone sélectionnée.
  import { Button } from '$lib/components/ui/button/index.js'
  let { titre = '', children } = $props()      // titre : le nom de la soirée ; children : l'intitulé du champ

  let ouvert = $state(false)
  let copie = $state('')
  let zone = $state(null)

  let prompt = $derived(`Donne-moi la liste des chansons de « ${titre || 'nom du concours, ville, année, finale ou demi-finale'} », dans l'ordre de passage.

Une ligne par chanson, colonnes séparées par un point-virgule, dans cet ordre :
Ordre;Pays;Artiste;Titre;Jury;Public;Rang

- Ordre = numéro de passage sur scène (1, 2, 3…).
- Pays en français (France, Suède, Royaume-Uni…).
- Si le concours a déjà eu lieu : Jury = points du jury, Public = points du télévote, Rang = place au classement final.
- S'il n'a pas encore eu lieu : laisse ces trois colonnes vides (1;France;Artiste;Titre;;;).
- Pas de numéro, pas de ligne d'en-tête, aucun autre texte : seulement les lignes, dans un bloc de code.`)

  async function copier() {
    copie = ''
    try {
      if (!window.isSecureContext || !navigator.clipboard) throw new Error('pas de presse-papiers moderne')
      await navigator.clipboard.writeText(prompt)
      copie = 'Copié.'
    } catch {
      zone?.select()
      try { copie = document.execCommand('copy') ? 'Copié.' : 'Sélectionné : copie-le à la main.' }
      catch { copie = 'Sélectionné : copie-le à la main.' }
    }
  }
  function touche(e) { if (e.key === 'Escape' && ouvert) ouvert = false }
</script>

<svelte:window onkeydown={touche} />

<div class="flex flex-wrap items-center gap-2">
  {@render children?.()}
  <button type="button" class="aide" aria-label="Un prompt pour obtenir la liste des chansons" aria-expanded={ouvert}
          onclick={() => { ouvert = !ouvert; copie = '' }}>?</button>
  {#if ouvert}
    <div class="bulle" role="dialog" aria-label="Prompt pour obtenir la liste">
      <p class="text-sm font-medium">Obtenir la liste avec une IA</p>
      <p class="mt-1 text-xs text-muted-foreground">Copie ce texte dans ChatGPT, Claude ou une autre IA, puis colle sa réponse ici. Les vrais votes, s'ils sont là, rempliront la fiche tout de suite : vérifie-les.</p>
      <textarea bind:this={zone} class="mt-2" readonly rows="11" value={prompt} aria-label="Texte du prompt"></textarea>
      <div class="mt-2 flex items-center gap-2">
        <Button size="sm" onclick={copier}>Copier</Button>
        <Button size="sm" variant="outline" onclick={() => (ouvert = false)}>Fermer</Button>
        {#if copie}<span class="text-xs text-muted-foreground" role="status">{copie}</span>{/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .aide { display: inline-grid; width: 1.6rem; height: 1.6rem; place-items: center; border-radius: 999px; border: 1px solid var(--border);
    font-size: 0.85rem; font-weight: 600; color: var(--muted-foreground); }
  .aide:hover, .aide[aria-expanded='true'] { color: var(--foreground); border-color: var(--primary); }
  .bulle { flex-basis: 100%; max-width: 34rem;
    border-radius: 1rem; border: 1px solid var(--border); background: var(--card); padding: 0.9rem; box-shadow: 0 10px 30px rgb(0 0 0 / 0.45); }
  textarea { width: 100%; resize: vertical; border-radius: 0.6rem; border: 1px solid var(--border); background: var(--background);
    padding: 0.5rem 0.6rem; font-size: 0.78rem; line-height: 1.4; color: var(--foreground); }
</style>
