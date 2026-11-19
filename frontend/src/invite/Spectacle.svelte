<script>
  // Le dévoilement sur le téléphone d'un invité (1.0). On regarde le concours à la télé : chacun suit le
  // classement sur son téléphone, l'hôte fait avancer les pas depuis le sien.
  // Pas 0 : le classement de l'invité, avec ses points. Puis tous les points du jury d'un coup, puis ceux des autres
  // invités chanson par chanson, de la plus mal placée par le jury à la mieux placée ; à chaque pas les totaux s'additionnent sur place,
  // puis les lignes prennent leur nouvelle place. Au dernier pas : le podium de la soirée, et sous lui celui de l'invité.
  import { onMount, onDestroy } from 'svelte'
  import { flip } from 'svelte/animate'
  import { cubicInOut } from 'svelte/easing'
  import { fade } from 'svelte/transition'
  import { drapeau, normaliser } from '$lib/pays.js'
  import Compteur from '$lib/Compteur.svelte'
  import Podium from './Podium.svelte'
  import DernierVote from '$lib/DernierVote.svelte'
  let { appel, regie = null } = $props()      // regie : la soirée vue par l'hôte connecté (lui seul fait avancer)

  let d = $state(null)
  let erreur = $state('')
  let triTotaux = $state({})                   // les totaux qui décident de l'ordre, avec un temps de retard
  let attente, minuterie, vu = -1
  let hauteur = $state(700)
  let animerDernier = $state(false)
  const RETARD_TRI = 1300

  async function lire() {
    if (document.hidden) return
    try {
      const n = await appel('GET', 'devoilement')
      n.chansons = n.chansons.map(normaliser)
      const premier = !d
      d = n
      if (n.pas !== vu) {
        // 1.7.0 : l'animation du dernier vote ne se joue que si ce téléphone a vu le pas d'avant (pas au rechargement)
        animerDernier = n.pas === n.fin - 1 && vu === n.fin - 2
        vu = n.pas
        clearTimeout(attente)
        if (premier) triTotaux = totaux()
        else attente = setTimeout(() => (triTotaux = totaux()), RETARD_TRI)
      }
      erreur = ''
    } catch (x) { erreur = x.message }
  }
  onMount(() => { hauteur = innerHeight; lire(); minuterie = setInterval(lire, 1000) })
  onDestroy(() => { clearInterval(minuterie); clearTimeout(attente) })

  let autres = $derived(d ? Object.fromEntries(d.public.map((x) => [x.chanson, x.autres])) : {})
  function lignesDe(x) {
    return x.chansons.map((c) => {
      const moi = x.moi?.points[c.id] || 0, jury = x.jury?.[c.id] || 0, pub = autres[c.id] || 0
      return { c, moi, jury, pub, total: moi + jury + pub }
    })
  }
  function totaux() { return Object.fromEntries(lignesDe(d).map((l) => [l.c.id, l.total])) }

  let fini = $derived(!!d && d.pas >= d.fin)
  let debut = $derived(d?.avec_jury ? 1 : 0)
  let appelee = $derived(d && !fini && d.pas > debut ? d.public[d.public.length - 1] : null)
  let phaseJury = $derived(!!d && d.avec_jury && d.pas === 1)
  let lignes = $derived.by(() => {
    if (!d) return []
    const l = lignesDe(d)
    if (fini && d.classement) {
      const rang = Object.fromEntries(d.classement.map((x, i) => [x.chanson, i]))
      return l.sort((a, b) => rang[a.c.id] - rang[b.c.id])
    }
    const t = (x) => triTotaux[x.c.id] ?? x.total
    return l.sort((a, b) => t(b) - t(a) || a.c.ordre - b.c.ordre)
  })
  let parId = $derived(d ? Object.fromEntries(d.chansons.map((c) => [c.id, c])) : {})
  // 1.7.0 : le dernier pas du public, joué par lib/DernierVote.svelte (comme à la télé)
  let dernierPas = $derived(!!d && !fini && !!appelee && d.pas === d.fin - 1)
  let totauxDernier = $derived(dernierPas ? Object.fromEntries(lignesDe(d).map((l) => [l.c.id, l.total])) : {})
  let ordreDernier = $derived(d ? [...d.chansons].sort((a, b) => a.ordre - b.ordre).map((c) => c.id) : [])
  // Toutes les chansons tiennent dans l'écran, sous le bandeau et au-dessus des commandes de l'hôte
  let h = $derived(d ? Math.min(40, Math.max(13, (hauteur - 150 - (regie ? 70 : 0)) / d.chansons.length - 2)) : 30)

  // ---- l'hôte
  let occupe = $state(false)
  async function aller(n) {
    if (!regie || occupe) return
    occupe = true
    try {
      const r = await fetch(`/api/soirees/${regie.id}/pas`, { method: 'POST', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ pas: Math.max(0, Math.min(d.fin, n)) }) })
      if (!r.ok) throw new Error(`Le serveur a répondu ${r.status}.`)
      await lire()
    } catch (x) { erreur = x.message } finally { occupe = false }
  }
  async function terminer() {
    if (!regie) return
    await fetch(`/api/soirees/${regie.id}/terminer`, { method: 'POST', credentials: 'same-origin' })
    await lire()
  }
  let monPodium = $derived(d?.moi ? Object.entries(d.moi.points).sort((a, b) => b[1] - a[1]).slice(0, 3)
    .map(([id, points]) => ({ c: parId[id], points })) : [])
  let podium = $derived(fini && d.classement ? d.classement.slice(0, 3).map((x) => ({ c: parId[x.chanson], points: x.total })) : [])
</script>

<svelte:window onresize={() => (hauteur = innerHeight)} />

<div class="spectacle fixed inset-0 z-20 flex flex-col bg-background px-3 pt-[calc(0.75rem+env(safe-area-inset-top))] pb-[calc(0.75rem+env(safe-area-inset-bottom))]">
  {#if !d}
    <p class="m-auto text-sm text-muted-foreground">{erreur || 'Le dévoilement commence…'}</p>
  {:else}
    <!-- Le bandeau : ce qui se passe à ce pas -->
    {#key d.pas}
      <div class="bandeau" class:jury={phaseJury} class:public={appelee} in:fade={{ duration: 250 }} role="status">
        {#if fini}<span>Le podium de la soirée</span>
        {:else if phaseJury}<span>Les points du jury</span>
        {:else if appelee}
          <span class="min-w-0 truncate">{drapeau(parId[appelee.chanson].pays, parId[appelee.chanson].code_pays)} {parId[appelee.chanson].pays} : <b>+{appelee.autres}</b> des autres invités</span>
          <span class="ml-auto shrink-0 text-xs opacity-75">{d.public.length} sur {d.nb_public}</span>
        {:else}<span>{d.moi ? 'Ton classement' : 'Le classement'}</span><span class="ml-auto text-xs opacity-75">en attente de l'hôte</span>{/if}
      </div>
    {/key}

    {#if fini}
      <div class="min-h-0 flex-1 overflow-y-auto pb-2">
        <Podium places={podium} />
        {#if monPodium.length}
          <p class="mt-5 text-center text-sm text-muted-foreground">Ton podium</p>
          <Podium places={monPodium} petit />
        {/if}
      </div>
    {:else if dernierPas}
      {#key d.pas}
        <div class="min-h-0 flex-1">
          <DernierVote chansons={d.chansons} totaux={totauxDernier} dernier={appelee.chanson} gain={appelee.autres}
                       ordre={ordreDernier} anime={animerDernier} compact />
        </div>
      {/key}
    {:else}
      <div class="entete" style="--h: {h}px" aria-hidden="true">
        <span class="flex-1">Pays</span>{#if d.moi}<span class="col moi">Moi</span>{/if}{#if d.avec_jury}<span class="col jury">Jury</span>{/if}<span class="col pub">Invités</span><span class="col tot">Total</span>
      </div>
      <ol class="grid content-start overflow-hidden" style="--h: {h}px; gap: 2px; grid-template-columns: minmax(0, 1fr)" aria-label="Classement en direct">
        {#each lignes as l, i (l.c.id)}
          <li animate:flip={{ duration: 900, easing: cubicInOut }}
              class="rangee" class:recu-jury={phaseJury && l.jury > 0} class:recu-public={appelee?.chanson === l.c.id}>
            <span class="rang">{i + 1}</span>
            <span class="min-w-0 flex-1 truncate">{drapeau(l.c.pays, l.c.code_pays)} {l.c.pays}</span>
            {#if d.moi}<span class="col moi">{l.moi || ''}</span>{/if}
            {#if d.avec_jury}<span class="col jury">{#if d.jury}<Compteur valeur={l.jury} />{/if}</span>{/if}
            <span class="col pub">{#if l.pub || autres[l.c.id] === 0}<Compteur valeur={l.pub} />{/if}</span>
            <span class="col tot chiffre"><Compteur valeur={l.total} retard={200} /></span>
          </li>
        {/each}
      </ol>
    {/if}

    {#if erreur}<p class="mt-1 text-center text-xs text-destructive" role="alert">{erreur}</p>{/if}

    {#if regie}
      <div class="mt-auto grid grid-cols-2 gap-2 pt-2" aria-label="Commandes de l'hôte">
        <button class="commande" onclick={() => aller(d.pas - 1)} disabled={d.pas === 0 || occupe}>Revenir</button>
        {#if fini}
          <button class="commande suivant" onclick={terminer} disabled={d.etat !== 'devoilement'}>{d.etat === 'devoilement' ? 'Terminer la soirée' : 'Soirée terminée'}</button>
        {:else}
          <button class="commande suivant" onclick={() => aller(d.pas + 1)} disabled={occupe}>Suivant</button>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .spectacle { --moi: #a98be6; --jury: #7aa2e3; --pub: var(--primary); }
  .bandeau { display: flex; align-items: center; gap: 0.5rem; min-height: 2.6rem; border-radius: 0.7rem; padding: 0.4rem 0.8rem; margin-bottom: 0.5rem; background: var(--card); font-size: 0.95rem; }
  .bandeau b { font-weight: 600; color: var(--pub); }
  .bandeau.jury { background: color-mix(in oklab, var(--jury) 25%, var(--background)); }
  .bandeau.public { background: color-mix(in oklab, var(--pub) 22%, var(--background)); }
  .entete { display: flex; gap: calc(var(--h) * 0.2); padding: 0 0.5rem 0.2rem; font-size: 0.68rem; color: var(--muted-foreground); }
  .rangee { display: flex; height: var(--h); align-items: center; gap: calc(var(--h) * 0.2); border-radius: 0.4rem; padding: 0 0.5rem;
    font-size: clamp(9px, calc(var(--h) * 0.46), 1rem); background: var(--background); }
  .rangee.recu-jury { background: color-mix(in oklab, var(--jury) 22%, var(--background)); }
  .rangee.recu-public { z-index: 1; background: color-mix(in oklab, var(--pub) 30%, var(--background)); box-shadow: inset 3px 0 0 var(--pub); }
  .rang { width: 1.3em; flex-shrink: 0; text-align: right; font-size: 0.75em; color: var(--muted-foreground); }
  .col { width: 2.4em; flex-shrink: 0; text-align: right; font-variant-numeric: tabular-nums; }
  .entete .col { width: calc(2.4 * clamp(9px, calc(var(--h) * 0.46), 1rem)); }
  .col.moi { color: var(--moi); }
  .col.jury { color: var(--jury); }
  .col.pub { color: var(--pub); }
  .col.tot { width: 2.6em; font-size: 1.2em; }
  .entete .col.tot { width: calc(3.1 * clamp(9px, calc(var(--h) * 0.46), 1rem)); color: var(--foreground); }
  .entete .col.moi, .entete .col.jury, .entete .col.pub { color: inherit; }
  .commande { min-height: 2.9rem; border-radius: 0.7rem; border: 1px solid var(--border); font-size: 1rem; }
  .commande.suivant { border: 0; background: #8f6ad8; color: #fff; font-weight: 500; }
  .commande:disabled { opacity: 0.45; }
</style>
