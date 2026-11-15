<script>
  // Le téléphone d'un invité : choisir son prénom, noter chaque chanson sur 20, ranger son classement, l'envoyer.
  // Tout passe par /invite/<jeton>/api/… ; le serveur ne rend jamais rien des autres avant la fin du dévoilement.
  import { onMount, onDestroy } from 'svelte'
  import { flip } from 'svelte/animate'
  import ChevronUp from '@lucide/svelte/icons/chevron-up'
  import ChevronDown from '@lucide/svelte/icons/chevron-down'
  import Grip from '@lucide/svelte/icons/grip-vertical'
  import { drapeau, EMISSIONS, BAREME, note, normaliser } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Embleme from '$lib/Embleme.svelte'
  import Ouverture from '$lib/Ouverture.svelte'
  let { jeton } = $props()

  const CLE = 'douze-points:' + jeton
  // Le jeton personnel du téléphone : gardé par le navigateur quand il le permet (pas en navigation privée stricte).
  let tel = ''
  try { tel = localStorage.getItem(CLE) || '' } catch { /* stockage fermé : le prénom tiendra le temps de la page */ }

  let e = $state(null)             // l'état de la soirée vu par ce téléphone
  let erreur = $state('')
  let ferme = $state(false)        // lien qui n'est plus valable
  let onglet = $state('chansons')
  let fiche = $state(null)         // chanson ouverte pour être notée
  let valeur = $state(10)
  let commentaire = $state('')
  let confirmer = $state(false)
  let resultats = $state(null)
  let occupe = 0                   // demandes en cours : la relecture n'écrase pas ce qu'on est en train de faire
  let glisse = $state(null)        // { id, depart, y } pendant un glisser
  let minuterie
  let touche = $state(false)       // la note ou le mot de la fiche ouverte ont été modifiés
  let regie = $state(null)         // pour l'hôte connecté à la régie : où en est chacun (jamais les notes)
  let estHote = false

  // L'hôte note sur la même page que ses invités. S'il est connecté à la régie sur cet appareil, l'onglet
  // « Les invités » lui montre en plus combien de chansons chacun a notées. Ni notes ni commentaires : surprise.
  async function lireRegie() {
    try {
      const soirees = await (await fetch('/api/soirees', { credentials: 'same-origin' })).json()
      for (const x of soirees.filter((y) => y.etat === 'ouverte')) {
        const d = await (await fetch('/api/soirees/' + x.id, { credentials: 'same-origin' })).json()
        if (d.jeton_invite === jeton) { regie = d; return }
      }
      regie = null
    } catch { regie = null }
  }

  async function appel(methode, suite, corps) {
    const r = await fetch(`/invite/${jeton}/api/${suite}`, {
      method: methode,
      headers: { ...(corps ? { 'Content-Type': 'application/json' } : {}), ...(tel ? { 'X-Telephone': tel } : {}) },
      body: corps ? JSON.stringify(corps) : undefined,
    })
    let donnees = null
    try { donnees = await r.json() } catch { /* sans contenu */ }
    if (!r.ok) throw Object.assign(new Error(donnees?.detail || `Le serveur a répondu ${r.status}.`), { statut: r.status })
    return donnees
  }

  async function ecrire(methode, suite, corps) {
    erreur = ''
    occupe++
    try {
      const d = await appel(methode, suite, corps)
      if (d?.moi) e.moi = d.moi
      return d
    } catch (x) {
      erreur = x.message
      if (x.statut === 403) { e.moi = null }      // prénom libéré par l'hôte : on le rechoisit
    } finally { occupe-- }
  }

  async function lire() {
    if (occupe || glisse || document.hidden) return
    try {
      const d = await appel('GET', 'etat')
      if (occupe || glisse) return
      e = d
      if (d.etat === 'devoilee' && !resultats) resultats = await appel('GET', 'resultats')
    } catch (x) {
      if (x.statut === 404) ferme = true
      else if (!e) erreur = "L'appli ne répond pas. Es-tu sur le Wi-Fi de la maison ?"
    }
  }

  onMount(async () => {
    lire()
    minuterie = setInterval(() => { lire(); if (estHote && onglet === 'invites' && !document.hidden) lireRegie() }, 3000)
    try {
      estHote = (await (await fetch('/api/session', { credentials: 'same-origin' })).json()).connecte === true
      if (estHote) lireRegie()
    } catch { estHote = false }
  })
  onDestroy(() => clearInterval(minuterie))

  async function choisir(p) {
    const d = await ecrire('POST', 'prenom', { participation_id: p.id })
    if (!d) return
    tel = d.jeton_telephone
    try { localStorage.setItem(CLE, tel) } catch { /* voir plus haut */ }
    await lire()
  }

  const image = (sorte) => (e?.images?.[sorte] ? `/invite/${jeton}/image/${sorte}?v=${e.images[sorte]}` : null)
  let chansons = $derived((e?.chansons || []).map(normaliser))
  let parId = $derived(Object.fromEntries(chansons.map((c) => [c.id, c])))
  let notes = $derived(e?.moi?.notes || {})
  let ordre = $derived(e?.moi?.classement || [])
  let nbNotees = $derived(Object.keys(notes).length)
  let envoye = $derived(e?.moi?.etat === 'envoye')
  let ouverte = $derived(e?.etat === 'ouverte')

  function ouvrir(c) {
    fiche = c
    valeur = notes[c.id]?.valeur ?? 10
    commentaire = notes[c.id]?.commentaire ?? ''
    touche = false
  }
  // « Enregistrer » enregistre et revient à la liste. « Précédente » et « Suivante » changent de chanson, en
  // enregistrant d'abord ce qui a été modifié ; une chanson ouverte sans rien toucher n'est pas notée par mégarde.
  async function enregistrer(pas = 0) {
    const c = fiche
    if (pas === 0 || touche) {
      await ecrire('PUT', 'note', { chanson_id: c.id, valeur, commentaire })
      if (erreur) return
    }
    const voisine = pas && chansons[chansons.findIndex((x) => x.id === c.id) + pas]
    if (voisine) ouvrir(voisine); else fiche = null
  }
  let rangFiche = $derived(fiche ? chansons.findIndex((x) => x.id === fiche.id) : -1)
  async function retirer() {
    await ecrire('PUT', 'note', { chanson_id: fiche.id, valeur: null })
    fiche = null
  }
  const pas = (d) => { valeur = Math.max(0, Math.min(20, Math.round((valeur + d) * 2) / 2)); touche = true }

  // ---- classement : flèches, ou glisser par la poignée
  const HAUTEUR = 56
  function deplacer(id, vers) {
    const de = ordre.indexOf(id)
    vers = Math.max(0, Math.min(ordre.length - 1, vers))
    if (de === vers) return false
    const nouveau = ordre.filter((x) => x !== id)
    nouveau.splice(vers, 0, id)
    e.moi.classement = nouveau
    return true
  }
  const envoyerOrdre = () => ecrire('PUT', 'classement', { ordre: e.moi.classement })
  function fleche(id, d) { if (deplacer(id, ordre.indexOf(id) + d)) envoyerOrdre() }
  function saisir(ev, id) {
    ev.currentTarget.setPointerCapture(ev.pointerId)
    glisse = { id, depart: ordre.indexOf(id), y: ev.clientY, bouge: false }
  }
  function tirer(ev) {
    if (!glisse) return
    const vers = glisse.depart + Math.round((ev.clientY - glisse.y) / HAUTEUR)
    if (deplacer(glisse.id, vers)) glisse.bouge = true
  }
  function lacher() {
    const bouge = glisse?.bouge
    glisse = null
    if (bouge) envoyerOrdre()
  }
  const auto = () => ecrire('PUT', 'classement', { auto: true })

  async function envoyer() {
    confirmer = false
    if (await ecrire('POST', 'envoyer')) await lire()
  }
  async function modifier() { if (await ecrire('POST', 'modifier')) await lire() }
</script>

<Ouverture />

<main class="mx-auto min-h-dvh max-w-lg px-4 pt-[calc(1rem+env(safe-area-inset-top))] pb-[calc(6.5rem+env(safe-area-inset-bottom))]">
  {#if ferme}
    <div class="grid min-h-[80dvh] place-items-center text-center">
      <div><p class="flex justify-center text-8xl"><Embleme src={image('logo')} /></p><p class="mt-4 text-lg">Cette soirée est terminée.</p><p class="text-sm text-muted-foreground">Le lien n'est plus valable.</p></div>
    </div>

  {:else if !e}
    <div class="grid min-h-[80dvh] place-items-center text-center">
      <div><p class="flex justify-center text-8xl"><Embleme src={image('logo')} /></p><p class="mt-4 text-sm text-muted-foreground" role="status">{erreur || 'Ouverture…'}</p></div>
    </div>

  {:else}
    {#if image('banniere')}<img src={image('banniere')} alt="" class="mb-3 max-h-36 w-full rounded-xl object-cover" />{/if}
    <header class="mb-4">
      <h1 class="text-2xl font-light tracking-tight">{e.nom}</h1>
      <p class="text-sm text-muted-foreground">{e.concours} {e.annee}, {EMISSIONS[e.emission].toLowerCase()}{e.moi ? ` · ${e.moi.prenom}` : ''}</p>
    </header>
    {#if erreur}<p class="mb-3 rounded-xl border border-destructive/60 px-4 py-2 text-sm" role="alert">{erreur}</p>{/if}

    {#if e.etat === 'brouillon'}
      <div class="mt-16 text-center"><p class="flex justify-center text-8xl"><Embleme src={image('logo')} /></p><p class="mt-6 text-xl font-light">Ça commence bientôt.</p>
        <p class="mt-2 text-sm text-muted-foreground">Garde cette page : elle s'ouvrira toute seule quand la soirée commencera.</p>
        {#if image('poster')}<img src={image('poster')} alt="Poster de l'évènement" class="mx-auto mt-6 max-h-[45dvh] rounded-xl object-contain" />{/if}</div>

    {:else if e.etat === 'devoilement'}
      <div class="mt-16 text-center"><p class="flex justify-center text-8xl"><Embleme src={image('logo')} /></p><p class="mt-6 text-xl font-light">Regarde la télé.</p>
        <p class="mt-2 text-sm text-muted-foreground">Les résultats arrivent ici dès que le dévoilement est fini.</p></div>

    {:else if e.etat === 'devoilee'}
      {#if resultats}
        <h2 class="text-lg font-semibold">Le classement de la soirée</h2>
        <ol class="mt-3 grid gap-1">
          {#each resultats.classement as l (l.chanson)}
            {@const c = parId[l.chanson]}
            <li class="flex min-h-11 items-center gap-3 rounded-lg px-3 {l.rang === 1 ? 'bg-primary text-primary-foreground' : 'bg-card'}">
              <span class="w-6 text-right text-sm opacity-70">{l.rang}</span><span>{drapeau(c.pays, c.code_pays)} {c.pays}</span>
              <span class="chiffre ml-auto text-xl">{l.total}</span>
            </li>
          {/each}
        </ol>
        {#each resultats.invites as inv (inv.id)}
          <h3 class="mt-6 font-semibold">{inv.prenom}</h3>
          <ul class="mt-2 grid gap-1 text-sm">
            {#each [...inv.points].reverse() as p}
              {@const c = parId[p.chanson]}
              <li class="flex gap-2"><span class="chiffre w-7 text-right text-base text-primary">{p.points}</span>
                <span class="min-w-0"><span>{drapeau(c.pays, c.code_pays)} {c.pays}</span> <span class="text-muted-foreground">{note(p.note)}/20</span>
                  {#if p.commentaire}<br /><span class="text-muted-foreground">« {p.commentaire} »</span>{/if}</span></li>
            {/each}
          </ul>
        {/each}
      {:else}<p class="text-sm text-muted-foreground">Lecture des résultats…</p>{/if}

    {:else if !e.moi}
      <h2 class="text-xl font-light">Qui es-tu ?</h2>
      <ul class="mt-4 grid grid-cols-2 gap-2">
        {#each e.invites as p (p.id)}
          <li><button class="prenom" disabled={p.pris} onclick={() => choisir(p)}>{p.prenom}{#if p.pris}<span class="block text-xs font-normal">déjà là</span>{/if}</button></li>
        {/each}
      </ul>
      <p class="mt-4 text-sm text-muted-foreground">Ton prénom est grisé alors que ce n'est pas toi ? Demande à l'hôte de le libérer.</p>

    {:else}
      {#if nbNotees === 0}
        <p class="mb-4 rounded-2xl border bg-card p-4 text-sm">Note chaque chanson sur 20. À la fin, range tes chansons : tes dix premières reçoivent 12, 10, 8, 7… 1 point. C'est ce classement qui compte.
          <button class="mt-1 block text-muted-foreground underline" onclick={() => { e.moi = null; tel = ''; try { localStorage.removeItem(CLE) } catch { /* rien */ } }}>Ce n'est pas mon prénom</button></p>
      {/if}

      {#if onglet === 'chansons'}
        <ol class="grid gap-1.5">
          {#each chansons as c (c.id)}
            <li><button class="chanson" class:en-cours={e.chanson_en_cours === c.id} onclick={() => ouvrir(c)}>
              <span class="w-6 shrink-0 text-right text-sm text-muted-foreground">{c.ordre}</span>
              <span class="shrink-0 text-2xl">{drapeau(c.pays, c.code_pays)}</span>
              <span class="min-w-0 flex-1 text-left"><span class="block truncate font-medium">{c.pays}</span>
                <span class="block truncate text-sm text-muted-foreground">{c.artiste}{c.titre ? ', ' + c.titre : ''}</span></span>
              {#if notes[c.id]}<span class="chiffre text-2xl">{note(notes[c.id].valeur)}</span>{:else}<span class="text-sm text-primary">Noter</span>{/if}
            </button></li>
          {/each}
        </ol>

      {:else if onglet === 'classement'}
        {#if !ordre.length}
          <p class="rounded-2xl border bg-card p-4 text-sm text-muted-foreground">Ton classement apparaîtra ici dès ta première note.</p>
        {:else}
          <p class="mb-3 text-sm text-muted-foreground">Rangé d'après tes notes. Glisse une ligne par sa poignée, ou utilise les flèches : tes notes ne changent pas.</p>
          <ol class="grid" style="touch-action: pan-y">
            {#each ordre as id, i (id)}
              {@const c = parId[id]}
              <li animate:flip={{ duration: 180 }} class="rang" class:tenu={glisse?.id === id} class:dixieme={i === 9 && ordre.length > 10} style="height: {HAUTEUR}px">
                <span class="chiffre w-8 shrink-0 text-right text-xl {i < 10 ? 'text-primary' : 'text-muted-foreground'}" title={i < 10 ? `${BAREME[i]} points` : 'aucun point'}>{i < 10 ? BAREME[i] : '·'}</span>
                <span class="min-w-0 flex-1"><span class="block truncate">{drapeau(c.pays, c.code_pays)} {c.pays}</span>
                  <span class="block text-xs text-muted-foreground">{i + 1}{i ? 'e' : 'er'} · noté {note(notes[id]?.valeur)}</span></span>
                {#if ouverte}
                  <button class="fleche" aria-label="Monter {c.pays}" disabled={i === 0} onclick={() => fleche(id, -1)}><ChevronUp class="size-5" /></button>
                  <button class="fleche" aria-label="Descendre {c.pays}" disabled={i === ordre.length - 1} onclick={() => fleche(id, 1)}><ChevronDown class="size-5" /></button>
                  <button class="fleche poignee" aria-label="Glisser {c.pays}" onpointerdown={(ev) => saisir(ev, id)} onpointermove={tirer} onpointerup={lacher} onpointercancel={lacher}><Grip class="size-5" /></button>
                {/if}
              </li>
            {/each}
          </ol>
          {#if e.moi.classement_main}<button class="mt-3 text-sm text-muted-foreground underline" onclick={auto}>Reclasser d'après mes notes</button>{/if}
        {/if}

      {:else}
        {#if regie}
          <!-- vue de l'hôte : où en est chacun, sans aucune note -->
          <p class="mb-3 flex items-center justify-between gap-3 text-sm">
            <span class="text-muted-foreground">{regie.participants.filter((p) => p.etat === 'envoye').length} classements envoyés sur {regie.participants.length}</span>
            <a class="underline" href="/">Retour à la régie</a>
          </p>
          <ul class="mb-4 grid gap-2" aria-label="Avancement des invités">
            {#each regie.participants as p (p.id)}
              <li class="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
                <span class="size-2.5 rounded-full {p.etat === 'envoye' ? 'bg-primary' : p.etat === 'en_cours' ? 'bg-foreground/50' : 'border border-muted-foreground'}"></span>
                <span class="font-medium">{p.prenom}</span>
                {#if p.jury}<span class="rounded-full border px-2 text-xs text-muted-foreground">jury</span>{/if}
                <span class="ml-auto text-sm text-muted-foreground">{p.etat === 'envoye' ? 'A envoyé' : p.etat === 'attendu' ? 'Pas arrivé' : `${p.notees} / ${chansons.length} notées`}</span>
              </li>
            {/each}
          </ul>
        {:else}
        <ul class="grid gap-2">
          {#each e.invites as p (p.id)}
            <li class="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
              <span class="size-2.5 rounded-full {p.envoye ? 'bg-primary' : p.pris ? 'bg-foreground/50' : 'border border-muted-foreground'}"></span>
              <span class="mr-auto font-medium">{p.prenom}</span>
              <span class="text-sm text-muted-foreground">{p.envoye ? 'A envoyé' : p.pris ? 'Note' : 'Pas arrivé'}</span>
            </li>
          {/each}
        </ul>
        {/if}
      {/if}

      <!-- Bas d'écran : l'envoi, puis les trois onglets -->
      <div class="fixed inset-x-0 bottom-0 z-10 border-t bg-background/95 px-4 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))] backdrop-blur">
        <div class="mx-auto max-w-lg">
          {#if envoye}
            <p class="flex items-center justify-between gap-3 text-sm"><span class="text-primary">Classement envoyé.</span>
              <button class="underline text-muted-foreground" onclick={modifier}>Modifier mon classement</button></p>
          {:else if nbNotees && onglet === 'chansons'}
            <!-- d'abord les notes, puis le classement : le gros bouton mène à l'étape suivante -->
            {#if nbNotees < chansons.length}<p class="mb-1 text-center text-xs text-muted-foreground">{chansons.length - nbNotees} chanson{chansons.length - nbNotees > 1 ? 's' : ''} pas encore notée{chansons.length - nbNotees > 1 ? 's' : ''}</p>{/if}
            <Button class="w-full" size="lg" variant={nbNotees < chansons.length ? 'outline' : 'default'} onclick={() => { fiche = null; onglet = 'classement'; scrollTo(0, 0) }}>Passer au classement</Button>
          {:else if nbNotees && onglet === 'classement'}
            <Button class="w-full" size="lg" onclick={() => (confirmer = true)}>Envoyer mon classement</Button>
          {/if}
          <nav class="mt-2 grid grid-cols-3 gap-1" aria-label="Sections">
            {#each [['chansons', `Chansons ${nbNotees}/${chansons.length}`], ['classement', 'Mon classement'], ['invites', 'Les invités']] as [cle, nom]}
              <button class="onglet" aria-current={onglet === cle ? 'page' : undefined} onclick={() => { onglet = cle; if (cle === 'invites' && estHote) lireRegie() }}>{nom}</button>
            {/each}
          </nav>
        </div>
      </div>
    {/if}
  {/if}
</main>

{#if fiche}
  <div class="fixed inset-0 z-20 flex flex-col bg-background px-5 pt-[calc(1rem+env(safe-area-inset-top))] pb-[calc(1rem+env(safe-area-inset-bottom))]" role="dialog" aria-label="Noter {fiche.pays}">
    <button class="self-start text-sm text-muted-foreground underline" onclick={() => (fiche = null)}>Retour à la liste</button>
    <p class="mt-4 text-sm text-muted-foreground">Chanson {fiche.ordre} sur {chansons.length}</p>
    <h2 class="text-3xl font-light tracking-tight">{drapeau(fiche.pays, fiche.code_pays)} {fiche.pays}</h2>
    <p class="text-muted-foreground">{fiche.artiste}{fiche.titre ? ', ' + fiche.titre : ''}</p>

    <div class="my-auto text-center">
      <p class="chiffre text-primary" style="font-size: 7.5rem" aria-live="polite">{note(valeur)}<span class="text-3xl text-muted-foreground"> /20</span></p>
      <div class="mt-4 flex items-center gap-3">
        <button class="demi" aria-label="Un demi-point de moins" onclick={() => pas(-0.5)}>−</button>
        <input type="range" min="0" max="20" step="0.5" bind:value={valeur} oninput={() => (touche = true)} aria-label="Note sur 20" class="curseur flex-1" />
        <button class="demi" aria-label="Un demi-point de plus" onclick={() => pas(0.5)}>+</button>
      </div>
    </div>

    <label class="champ">Un mot sur cette chanson (facultatif, signé de ton prénom au dévoilement)
      <textarea bind:value={commentaire} oninput={() => (touche = true)} rows="2" maxlength="280"></textarea>
    </label>
    {#if erreur}<p class="mt-2 text-sm text-destructive" role="alert">{erreur}</p>{/if}
    <p class="mt-2 flex min-h-5 items-center text-xs text-muted-foreground">
      {#if notes[fiche.id]}<button class="underline" onclick={retirer}>Retirer ma note</button>
      {:else if !touche}Pas encore notée : bouge le curseur, ou passe à une autre chanson.{/if}
    </p>
    <div class="mt-2 grid grid-cols-3 gap-2">
      <Button variant="outline" size="lg" onclick={() => enregistrer(-1)} disabled={rangFiche <= 0}>Précédente</Button>
      <Button size="lg" onclick={() => enregistrer(0)}>Enregistrer</Button>
      <Button variant="outline" size="lg" onclick={() => enregistrer(1)} disabled={rangFiche >= chansons.length - 1}>Suivante</Button>
    </div>
  </div>
{/if}

{#if confirmer}
  <div class="fixed inset-0 z-20 grid place-items-end bg-black/60 p-4 sm:place-items-center" role="alertdialog" aria-label="Envoyer mon classement">
    <div class="w-full max-w-md rounded-2xl border bg-card p-5">
      <h2 class="text-lg font-semibold">Envoyer mon classement ?</h2>
      {#if nbNotees < chansons.length}
        <p class="mt-2 text-sm">Tu n'as pas noté {chansons.length - nbNotees} chanson{chansons.length - nbNotees > 1 ? 's' : ''} : elles ne recevront aucun point de toi.</p>
      {/if}
      <p class="mt-2 text-sm text-muted-foreground">Tu pourras encore le modifier tant que le dévoilement n'a pas commencé.</p>
      <div class="mt-4 flex justify-end gap-2"><Button variant="outline" onclick={() => (confirmer = false)}>Pas encore</Button><Button onclick={envoyer}>Envoyer mon classement</Button></div>
    </div>
  </div>
{/if}

<style>
  .prenom { width: 100%; min-height: 4rem; border-radius: 1rem; border: 1px solid var(--border); background: var(--card); font-size: 1.15rem; font-weight: 500; }
  .prenom:disabled { opacity: 0.4; cursor: default; }
  .chanson { display: flex; width: 100%; min-height: 3.75rem; align-items: center; gap: 0.75rem; border-radius: 0.9rem; border: 1px solid var(--border); background: var(--card); padding: 0.4rem 0.9rem; }
  .chanson.en-cours { border-color: var(--primary); box-shadow: inset 3px 0 0 var(--primary); }
  .rang { display: flex; align-items: center; gap: 0.6rem; border-bottom: 1px solid var(--border); background: var(--background); }
  .rang.dixieme { border-bottom: 2px solid var(--primary); }
  .rang.tenu { position: relative; z-index: 1; background: var(--card); box-shadow: 0 6px 18px rgb(0 0 0 / 0.45); }
  .fleche { display: grid; width: 2.75rem; height: 2.75rem; place-items: center; border-radius: 0.6rem; color: var(--muted-foreground); }
  .fleche:disabled { opacity: 0.25; cursor: default; }
  .poignee { touch-action: none; cursor: grab; }
  .onglet { min-height: 2.75rem; border-radius: 0.7rem; font-size: 0.85rem; color: var(--muted-foreground); }
  .onglet[aria-current="page"] { background: var(--secondary); color: var(--foreground); }
  .demi { width: 3.25rem; height: 3.25rem; border-radius: 999px; border: 1px solid var(--border); font-size: 1.6rem; font-weight: 300; }
  .curseur { height: 3rem; accent-color: var(--primary); }
</style>
