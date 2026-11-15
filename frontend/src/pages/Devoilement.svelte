<script>
  // Le dévoilement, joué sur le téléphone de l'hôte (en paysage, recopié sur la télé) à partir des points figés.
  // Toucher l'écran : pas suivant. Le pas est gardé côté serveur : après une coupure, on reprend où l'on était.
  import { onMount } from 'svelte'
  import { flip } from 'svelte/animate'
  import { fade, scale } from 'svelte/transition'
  import { api } from '$lib/api.js'
  import { drapeau, note } from '$lib/pays.js'
  import Embleme from '$lib/Embleme.svelte'
  let { soiree, onferme } = $props()

  let d = $state(null)
  let erreur = $state('')
  let pas = $state(0)
  let lignesVisibles = $state(10)

  // Les pas : pour chaque invité, ses petits points d'un coup (mode court : 1 à 7), puis ses grands un par un.
  let etapes = $derived.by(() => {
    if (!d) return []
    const sortie = []
    for (const inv of d.invites) {
      const seuil = d.mode === 'court' ? 8 : 0
      const petits = inv.points.filter((p) => p.points < seuil)
      if (petits.length) sortie.push({ invite: inv, lot: petits })
      for (const p of inv.points.filter((x) => x.points >= seuil)) sortie.push({ invite: inv, lot: [p], annonce: p })
    }
    return sortie
  })
  let fini = $derived(d && pas >= etapes.length)
  let courant = $derived(pas > 0 && !fini ? etapes[pas - 1] : null)
  let chansons = $derived(d ? Object.fromEntries(d.chansons.map((c) => [c.id, c])) : {})

  // Le tableau : pendant le jeu, les totaux des pas déjà joués ; à la fin, le classement du serveur (égalités départagées).
  let tableau = $derived.by(() => {
    if (!d) return []
    if (fini) return d.classement.map((l) => ({ ...l, c: chansons[l.chanson] }))
    const totaux = Object.fromEntries(d.chansons.map((c) => [c.id, 0]))
    for (const e of etapes.slice(0, pas)) for (const p of e.lot) totaux[p.chanson] += p.points
    return d.chansons.map((c) => ({ chanson: c.id, total: totaux[c.id], c }))
      .sort((a, b) => b.total - a.total || a.c.ordre - b.c.ordre)
  })
  let recu = $derived(new Set(courant ? courant.lot.map((p) => p.chanson) : []))

  function mesurer() { lignesVisibles = Math.max(5, Math.floor((window.innerHeight - 40) / 44)) }

  onMount(async () => {
    mesurer()
    try {
      d = await api.get(`/api/soirees/${soiree}/devoilement`)
      pas = Math.min(d.pas, etapes.length)
    } catch (e) { erreur = e.message }
  })

  function aller(n) {
    pas = Math.max(0, Math.min(etapes.length, n))
    api.post(`/api/soirees/${soiree}/pas`, { pas }).catch(() => {})   // une soirée déjà dévoilée ne garde plus le pas : sans importance
  }
  async function terminer() {
    try { await api.post(`/api/soirees/${soiree}/terminer`) } catch { /* déjà terminée : on rejoue une archive */ }
    onferme()
  }
  function touche(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') aller(pas + 1)
    if (e.key === 'ArrowLeft') aller(pas - 1)
  }
</script>

<svelte:window onresize={mesurer} onkeydown={touche} />

<div class="fixed inset-0 z-30 bg-background">
  {#if erreur}
    <div class="grid h-full place-items-center p-6 text-center">
      <div><p role="alert">{erreur}</p><button class="pastille mt-4" onclick={onferme}>Fermer</button></div>
    </div>
  {:else if d}
    <!-- Toute la surface avance d'un pas ; les trois commandes discrètes sont posées par-dessus -->
    <button class="absolute inset-0 cursor-default" aria-label="Pas suivant" onclick={() => (fini ? null : aller(pas + 1))}></button>

    <div class="pointer-events-none relative grid h-full gap-x-8 p-[max(1rem,env(safe-area-inset-top))] landscape:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <ol class="grid content-start gap-1 overflow-hidden" aria-label="Classement du groupe">
        {#each tableau.slice(0, lignesVisibles) as l, i (l.chanson)}
          <li animate:flip={{ duration: 450 }} class="flex h-10 items-center gap-3 rounded-lg px-3 text-lg {recu.has(l.chanson) ? 'bg-primary text-primary-foreground' : i === 0 && pas > 0 ? 'bg-card' : ''}">
            <span class="w-6 text-right text-sm opacity-60">{fini ? l.rang : i + 1}</span>
            <span class="text-xl">{drapeau(l.c.pays, l.c.code_pays)}</span>
            <span class="truncate">{l.c.pays}</span>
            <span class="chiffre ml-auto text-2xl">{l.total}</span>
          </li>
        {/each}
      </ol>

      <div class="grid content-center justify-items-center overflow-hidden pt-10 text-center portrait:hidden">
        {#if pas === 0}
          <p style="font-size: 30vh; line-height: 1"><Embleme src={d.images.logo ? `/api/soirees/${soiree}/image/logo?v=${d.images.logo}` : null} /></p>
          <p class="mt-2 text-2xl font-light">Le classement de la soirée</p>
          <p class="mt-3 text-muted-foreground">{d.invites.length} classements. Touche l'écran pour commencer.</p>
        {:else if fini}
          {@const podium = tableau.slice(0, 3)}
          <p class="text-2xl font-light text-muted-foreground">Le choix de la soirée</p>
          <p class="mt-2" style="font-size: 14vh; line-height: 1">{drapeau(podium[0].c.pays, podium[0].c.code_pays)}</p>
          <p class="mt-1 font-light tracking-tight" style="font-size: clamp(1.8rem, 11vh, 4rem); line-height: 1.1">{podium[0].c.pays}</p>
          <p class="text-lg text-muted-foreground">{podium[0].c.artiste}{podium[0].c.titre ? ', ' + podium[0].c.titre : ''}</p>
          <p class="chiffre mt-2 text-primary" style="font-size: 13vh">{podium[0].total}</p>
          {#if podium.length > 1}
            <p class="mt-2 text-lg text-muted-foreground">puis {podium.slice(1).map((p) => `${p.c.pays} (${p.total})`).join(' et ')}</p>
          {/if}
        {:else}
          {#key pas}
            <div in:fade={{ duration: 200 }}>
              <p class="text-3xl font-light">{courant.invite.prenom}</p>
              {#if !courant.invite.envoye || courant.invite.notees < d.chansons.length}
                <p class="text-sm text-muted-foreground">{courant.invite.notees} chansons sur {d.chansons.length}</p>
              {/if}
              {#if courant.annonce}
                {@const c = chansons[courant.annonce.chanson]}
                <p class="chiffre mt-1 text-primary" style="font-size: 24vh" in:scale={{ start: 0.7, duration: 350 }}>{courant.annonce.points}</p>
                <p class="text-lg text-muted-foreground">{courant.annonce.points === 12 ? 'Douze points' : 'points'}</p>
                <p class="mt-1 font-light tracking-tight" style="font-size: clamp(1.8rem, 11vh, 4rem); line-height: 1.1">{drapeau(c.pays, c.code_pays)} {c.pays}</p>
                <p class="text-base text-muted-foreground">noté {note(courant.annonce.note)} sur 20</p>
                {#if courant.annonce.commentaire}<p class="mx-auto mt-1 line-clamp-2 max-w-md text-lg">« {courant.annonce.commentaire} »</p>{/if}
              {:else}
                <p class="mt-6 text-2xl text-muted-foreground">Ses points de 1 à 7</p>
              {/if}
            </div>
          {/key}
        {/if}
      </div>
    </div>

    <div class="absolute inset-x-0 top-[max(0.5rem,env(safe-area-inset-top))] flex justify-end gap-2 px-4 text-xs">
      <p class="mr-auto self-center text-muted-foreground landscape:hidden">Tourne le téléphone en paysage.</p>
      {#if pas > 0}<button class="commande" onclick={() => aller(pas - 1)}>Revenir</button>{/if}
      {#if !fini}<button class="commande" onclick={() => aller(etapes.length)}>Tout afficher</button>{/if}
      {#if fini}<button class="commande plein" onclick={terminer}>Terminer</button>{:else}<button class="commande" onclick={onferme}>Fermer</button>{/if}
    </div>
  {/if}
</div>

<style>
  .commande { min-height: 2.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--background); padding: 0 1rem; color: var(--muted-foreground); }
  .commande.plein { background: var(--primary); color: var(--primary-foreground); border-color: var(--primary); }
</style>
