<script>
  // Les trois images de l'évènement, déposées par l'hôte : logo, bannière, poster. Toutes facultatives.
  import { Button } from '$lib/components/ui/button/index.js'
  let { soiree, onchange } = $props()

  const sortes = [
    { cle: 'logo', nom: 'Logo', ou: "À la place du « 12 » : écran d'accueil, affiche à partager, écrans d'attente, départ du dévoilement." },
    { cle: 'banniere', nom: 'Bannière', ou: 'En haut du téléphone des invités, sur toute la largeur.' },
    { cle: 'poster', nom: 'Poster', ou: "Sur l'écran d'accueil et l'affiche, à côté du QR code, et sur l'écran « Ça commence bientôt »." },
  ]
  let erreur = $state('')
  let envoi = $state('')

  async function deposer(sorte, fichier) {
    if (!fichier) return
    erreur = ''
    envoi = sorte
    try {
      const r = await fetch(`/api/soirees/${soiree.id}/image/${sorte}`, { method: 'PUT', body: fichier, credentials: 'same-origin' })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || `Le serveur a répondu ${r.status}.`)
      await onchange()
    } catch (e) { erreur = e.message } finally { envoi = '' }
  }
  async function retirer(sorte) {
    erreur = ''
    const r = await fetch(`/api/soirees/${soiree.id}/image/${sorte}`, { method: 'DELETE', credentials: 'same-origin' })
    if (!r.ok) erreur = "L'image n'a pas pu être retirée."
    await onchange()
  }
</script>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Images de l'évènement</h2>
  <p class="text-sm text-muted-foreground">Facultatif. PNG, JPEG ou WebP, 6 Mo au plus. Sans logo, c'est le « 12 » de l'appli.</p>
  {#if erreur}<p class="mt-2 text-sm text-destructive" role="alert">{erreur}</p>{/if}
  <ul class="mt-4 grid gap-3 sm:grid-cols-3">
    {#each sortes as s (s.cle)}
      <li class="flex flex-col gap-2 rounded-xl border p-3">
        <p class="font-medium">{s.nom}</p>
        <div class="grid h-28 place-items-center overflow-hidden rounded-lg bg-background">
          {#if soiree.images[s.cle]}
            <img src="/api/soirees/{soiree.id}/image/{s.cle}?v={soiree.images[s.cle]}" alt="{s.nom} de l'évènement" class="max-h-28 max-w-full object-contain" />
          {:else}
            <span class="text-sm text-muted-foreground">Aucune image</span>
          {/if}
        </div>
        <p class="text-xs text-muted-foreground">{s.ou}</p>
        <div class="mt-auto flex flex-wrap gap-2">
          <label class="depot">
            {envoi === s.cle ? 'Envoi…' : soiree.images[s.cle] ? 'Remplacer' : 'Choisir une image'}
            <input type="file" accept="image/png,image/jpeg,image/webp" class="sr-only" aria-label="{s.nom} : choisir une image"
              onchange={(e) => { deposer(s.cle, e.currentTarget.files[0]); e.currentTarget.value = '' }} />
          </label>
          {#if soiree.images[s.cle]}<Button variant="outline" size="sm" onclick={() => retirer(s.cle)} aria-label="Retirer : {s.nom}">Retirer</Button>{/if}
        </div>
      </li>
    {/each}
  </ul>
</section>

<style>
  .depot { display: inline-flex; min-height: 2rem; cursor: pointer; align-items: center; border-radius: 0.6rem; border: 1px solid var(--border); padding: 0 0.75rem; font-size: 0.85rem; font-weight: 500; }
  .depot:focus-within { border-color: var(--ring); }
</style>
