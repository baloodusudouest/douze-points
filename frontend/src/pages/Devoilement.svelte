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

  // Les pas.
  // « court » et « complet » : invité par invité, ses petits points d'un coup (court : 1 à 7), puis ses grands un par un.
  // « jury » : comme au concours. D'abord les points du jury, chanson par chanson dans l'ordre de passage ;
  // puis ceux du public, en partant de la dernière du classement du jury et en remontant jusqu'à la première.
  let etapes = $derived.by(() => {
    if (!d) return []
    const sortie = []
    if (d.mode === 'jury') {
      const recus = (jury) => {
        const parChanson = Object.fromEntries(d.chansons.map((c) => [c.id, []]))
        for (const inv of d.invites.filter((i) => i.jury === jury))
          for (const p of inv.points) parChanson[p.chanson].push({ ...p, prenom: inv.prenom })
        return parChanson
      }
      const jury = recus(true), publicc = recus(false)
      const somme = (lot) => lot.reduce((t, p) => t + p.points, 0)
      for (const c of d.chansons)
        sortie.push({ phase: 'jury', chanson: c.id, lot: jury[c.id], total: somme(jury[c.id]) })
      const remontee = [...d.chansons].sort((x, y) => somme(jury[x.id]) - somme(jury[y.id]) || y.ordre - x.ordre)
      for (const c of remontee)
        sortie.push({ phase: 'public', chanson: c.id, lot: publicc[c.id], total: somme(publicc[c.id]) })
      return sortie
    }
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
  let recu = $derived(new Set(courant ? (courant.phase ? [courant.chanson] : courant.lot.map((p) => p.chanson)) : []))

  // Cotillons du podium : une centaine de papiers, chacun avec sa place, sa couleur, sa durée et son retard.
  const COULEURS = ['#e5559f', '#f2ece2', '#a98fd8', '#7f9cc4', '#8fae6b', '#e0884a']
  const cotillons = Array.from({ length: 110 }, (_, i) => ({
    gauche: Math.random() * 100, retard: Math.random() * 2.5, duree: 2.8 + Math.random() * 2.6,
    couleur: COULEURS[i % COULEURS.length], largeur: 6 + Math.random() * 6, tourne: Math.random() * 360, rond: i % 4 === 0,
  }))

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
          <p class="text-xl font-light text-muted-foreground">Le podium de la soirée</p>
          <!-- le podium : la deuxième à gauche, la première au milieu et plus haut, la troisième à droite -->
          <ol class="podium mt-1" aria-label="Podium">
            {#each [1, 0, 2] as place}
              {#if podium[place]}
                <li class="marche m{place + 1}" style="order: {[1, 0, 2].indexOf(place)}">
                  <span class="drap">{drapeau(podium[place].c.pays, podium[place].c.code_pays)}</span>
                  <span class="pays">{podium[place].c.pays}</span>
                  <span class="chiffre points">{podium[place].total}</span>
                  <span class="socle"><span class="chiffre">{place + 1}</span></span>
                </li>
              {/if}
            {/each}
          </ol>
          <p class="mt-1 text-sm text-muted-foreground">{podium[0].c.artiste}{podium[0].c.titre ? ', ' + podium[0].c.titre : ''}</p>
        {:else}
          {#key pas}
            {#if courant.phase}
              {@const c = chansons[courant.chanson]}
              <div in:fade={{ duration: 200 }}>
                <p class="text-2xl font-light text-muted-foreground">{courant.phase === 'jury' ? 'Les points du jury' : 'Les points du public'}</p>
                <p class="mt-2 font-light tracking-tight" style="font-size: clamp(1.8rem, 11vh, 4rem); line-height: 1.1">{drapeau(c.pays, c.code_pays)} {c.pays}</p>
                <p class="chiffre mt-1 text-primary" style="font-size: 24vh" in:scale={{ start: 0.7, duration: 350 }}>{courant.total}</p>
                <p class="text-lg text-muted-foreground">{courant.total > 1 ? 'points' : 'point'}</p>
                {#if courant.phase === 'jury' && courant.lot.length}
                  <p class="mx-auto mt-2 line-clamp-2 max-w-md text-base text-muted-foreground">{[...courant.lot].sort((x, y) => y.points - x.points).map((p) => `${p.points} de ${p.prenom}`).join(', ')}</p>
                {/if}
              </div>
            {:else}
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
            {/if}
          {/key}
        {/if}
      </div>
    </div>

    {#if fini}
      <div class="cotillons" aria-hidden="true">
        {#each cotillons as k}
          <i style="left: {k.gauche}%; width: {k.largeur}px; height: {k.rond ? k.largeur : k.largeur * 1.8}px; background: {k.couleur}; border-radius: {k.rond ? '50%' : '1px'}; animation-duration: {k.duree}s; animation-delay: {k.retard}s; --tourne: {k.tourne}deg"></i>
        {/each}
      </div>
    {/if}

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

  .podium { display: flex; align-items: flex-end; justify-content: center; gap: 1.2vw; }
  .marche { display: flex; width: 11vw; min-width: 4.5rem; flex-direction: column; align-items: center; animation: monter 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .marche .drap { font-size: 7vh; line-height: 1.1; }
  .marche .pays { margin-top: 0.2rem; max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: clamp(0.85rem, 3.8vh, 1.4rem); line-height: 1.2; }
  .marche .points { font-size: 5vh; line-height: 1.1; color: var(--primary); }
  .marche .socle { display: grid; width: 100%; place-items: start center; border-radius: 0.5rem 0.5rem 0 0; background: var(--card); border: 1px solid var(--border); border-bottom: 0; padding-top: 0.3vh; font-size: 3.6vh; line-height: 1.2; color: var(--muted-foreground); }
  .m1 .socle { height: 15vh; background: var(--primary); color: var(--primary-foreground); border-color: var(--primary); }
  .m2 .socle { height: 10vh; }
  .m3 .socle { height: 6vh; }
  .m3 { animation-delay: 0.15s; } .m2 { animation-delay: 0.45s; } .m1 { animation-delay: 0.8s; }
  @keyframes monter { from { opacity: 0; transform: translateY(8vh); } to { opacity: 1; transform: none; } }

  .cotillons { pointer-events: none; position: absolute; inset: 0; overflow: hidden; }
  .cotillons i { position: absolute; top: -4vh; opacity: 0; animation: tomber linear infinite; }
  @keyframes tomber {
    0% { opacity: 1; transform: translateY(0) rotate(var(--tourne)); }
    100% { opacity: 1; transform: translateY(108vh) rotate(calc(var(--tourne) + 540deg)); }
  }
  @media (prefers-reduced-motion: reduce) {
    .cotillons { display: none; }
    .marche { animation: none; }
  }
</style>
