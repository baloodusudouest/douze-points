<script>
  // Le dévoilement, joué sur le téléphone de l'hôte (en paysage, recopié sur la télé) à partir des points figés.
  // Toucher l'écran : pas suivant. Le pas est gardé côté serveur : après une coupure, on reprend où l'on était.
  import { onMount, onDestroy } from 'svelte'
  import { flip } from 'svelte/animate'
  import { cubicInOut } from 'svelte/easing'
  import { fade, scale } from 'svelte/transition'
  import { api } from '$lib/api.js'
  import { drapeau, note, normaliser } from '$lib/pays.js'
  import Embleme from '$lib/Embleme.svelte'
  import Compteur from '$lib/Compteur.svelte'
  import EcranJumeaux from './EcranJumeaux.svelte'
  import DernierVote from '$lib/DernierVote.svelte'
  let { soiree, onferme } = $props()

  let d = $state(null)
  let erreur = $state('')
  let pas = $state(0)
  // L'ordre du tableau suit le pas avec un temps de retard : d'abord les points s'additionnent dans la ligne,
  // puis la ligne glisse à sa nouvelle place.
  let pasTri = $state(0)
  let attenteTri
  const RETARD_TRI = 1300
  let hauteurEcran = $state(800)

  // Les pas (1.0), les mêmes que sur les téléphones des invités (le serveur les fixe : d.marche) :
  // tous les points du jury d'un coup, puis ceux du public chanson par chanson, de la plus mal placée par le jury à la mieux placée (1.6.1).
  let etapes = $derived.by(() => {
    if (!d) return []
    const jures = new Set(d.marche.jures)
    const parChanson = (jury) => {
      const lot = Object.fromEntries(d.chansons.map((c) => [c.id, []]))
      for (const inv of d.invites.filter((i) => jures.has(i.id) === jury))
        for (const p of inv.points) lot[p.chanson].push({ ...p, prenom: inv.prenom })
      return lot
    }
    const somme = (lot) => lot.reduce((t, p) => t + p.points, 0)
    const jury = parChanson(true), publicc = parChanson(false)
    const sortie = []
    if (jures.size) {
      const tous = Object.values(jury).flat()
      const top = [...d.chansons].sort((x, y) => somme(jury[y.id]) - somme(jury[x.id]) || x.ordre - y.ordre)
        .slice(0, 5).map((c) => ({ chanson: c.id, points: somme(jury[c.id]) }))
      sortie.push({ phase: 'top', jury: true, lot: tous, top })
    }
    for (const id of d.marche.public)
      sortie.push({ phase: 'public', chanson: id, lot: publicc[id], total: somme(publicc[id]), avant: somme(jury[id]) })
    return sortie
  })
  // pas 0 : l'attente ; pas 1 à N : les étapes ; pas N + 1 : le podium.
  let fin = $derived(etapes.length + 1)
  let fini = $derived(!!d && pas >= fin)
  let courant = $derived(pas > 0 && !fini ? etapes[pas - 1] : null)
  let chansons = $derived(d ? Object.fromEntries(d.chansons.map((c) => [c.id, c])) : {})
  let avecJury = $derived(!!d?.marche.jures.length)

  // Le tableau : pendant le jeu, les totaux des pas déjà joués ; à la fin, le classement du serveur (égalités départagées).
  // Points reçus jusqu'à un pas donné, séparés jury / public (en mode « jury puis public »)
  function cumul(jusque) {
    const jury = Object.fromEntries(d.chansons.map((c) => [c.id, 0]))
    const pub = Object.fromEntries(d.chansons.map((c) => [c.id, 0]))
    for (const e of etapes.slice(0, jusque)) for (const p of e.lot) (e.jury ? jury : pub)[p.chanson] += p.points
    return { jury, pub }
  }
  let tableau = $derived.by(() => {
    if (!d) return []
    const affiche = cumul(Math.min(pas, etapes.length))
    const lignes = d.chansons.map((c) => ({ chanson: c.id, c, jury: affiche.jury[c.id], pub: affiche.pub[c.id],
                                           total: affiche.jury[c.id] + affiche.pub[c.id] }))
    if (pasTri >= fin) {          // le classement du serveur, avec ses égalités départagées
      const rang = Object.fromEntries(d.classement.map((l, i) => [l.chanson, { i, rang: l.rang }]))
      return lignes.map((l) => ({ ...l, rang: rang[l.chanson].rang })).sort((a, b) => rang[a.chanson].i - rang[b.chanson].i)
    }
    const tri = cumul(Math.min(pasTri, etapes.length))
    const t = (id) => tri.jury[id] + tri.pub[id]
    return lignes.sort((a, b) => t(b.chanson) - t(a.chanson) || a.c.ordre - b.c.ordre)
  })
  let plus = $derived(Math.max(1, ...tableau.map((l) => l.total)))
  let recu = $derived(new Set(courant ? (courant.chanson ? [courant.chanson] : courant.lot.map((p) => p.chanson)) : []))
  let teinte = $derived(courant?.jury ? 'jury' : 'public')
  // 1.7.0 : le dernier pas du public joue l'animation du dernier vote (lib/DernierVote.svelte) à la place du tableau.
  // Elle ne se joue que si l'on vient du pas d'avant (« Suivant », ou le téléphone de l'hôte) ; au rechargement ou en
  // revenant du podium, l'écran montre directement la fin.
  let dernierPas = $derived(!!courant && courant.phase === 'public' && pas === etapes.length)
  let animerDernier = $state(false)
  let totauxDernier = $derived.by(() => {
    if (!dernierPas) return {}
    const c = cumul(pas)
    return Object.fromEntries(d.chansons.map((x) => [x.id, c.jury[x.id] + c.pub[x.id]]))
  })

  // Cotillons du podium : une centaine de papiers, chacun avec sa place, sa couleur, sa durée et son retard.
  const COULEURS = ['#e5559f', '#f2ece2', '#a98fd8', '#7f9cc4', '#8fae6b', '#e0884a']
  const cotillons = Array.from({ length: 110 }, (_, i) => ({
    gauche: Math.random() * 100, retard: Math.random() * 2.5, duree: 2.8 + Math.random() * 2.6,
    couleur: COULEURS[i % COULEURS.length], largeur: 6 + Math.random() * 6, tourne: Math.random() * 360, rond: i % 4 === 0,
  }))

  function mesurer() { hauteurEcran = window.innerHeight }
  // Toutes les chansons tiennent dans la hauteur de l'écran : sur la télé les lignes gardent leur taille,
  // sur un iPhone elles rapetissent (quitte à devenir minuscules) plutôt que d'être coupées.
  let hauteurLigne = $derived(d ? Math.min(46, Math.max(6, (hauteurEcran - 40 - (avecJury ? 20 : 0)) / d.chansons.length - 2)) : 36)

  // Sur l'iPhone, un glissement du doigt de gauche à droite referme l'écran (les boutons deviennent petits).
  let depart = null
  function doigtPose(e) { const t = e.touches[0]; depart = { x: t.clientX, y: t.clientY } }
  function doigtLeve(e) {
    if (!depart) return
    const t = e.changedTouches[0], dx = t.clientX - depart.x, dy = Math.abs(t.clientY - depart.y)
    depart = null
    if (dx > 90 && dy < dx / 2) onferme()
  }

  // 1.8 : le pas est tenu par le serveur (conseil 1.8.0). Les points du public passent seuls toutes les 5 s ; cet écran
  // n'envoie jamais un numéro de pas, seulement des actions (suivant, revenir, pause, reprendre, aller), et prend le pas
  // que le serveur lui rend. Il relit le serveur chaque seconde, et tout de suite à l'échéance d'un pays.
  let auto = $state(null)          // { actif, pause, prochain_dans, duree } tel que lu
  let luA = $state(0)              // heure de la lecture de `auto` (horloge de cet écran)
  let maintenantMs = $state(Date.now())
  let charge = false               // le premier pas lu au chargement ne rejoue pas d'animation
  let gestes = 0                   // une lecture partie avant un geste est ignorée : elle date d'avant lui
  let echeance

  function appliquer(lu) {
    if (lu.pas === null || lu.pas === undefined) return
    auto = lu.auto || null
    luA = Date.now()
    clearTimeout(echeance)
    if (auto?.actif && !auto.pause && auto.prochain_dans !== null)
      echeance = setTimeout(relire, auto.prochain_dans + 60)     // le pays suivant, à l'heure du serveur
    if (lu.pas !== pas || !charge) aller(lu.pas)
    charge = true
  }
  async function relire() {
    if (!d || document.hidden) return
    const g = gestes
    try {
      const lu = await api.get(`/api/soirees/${soiree}/devoilement`)
      if (g === gestes && lu.etat === 'devoilement') appliquer(lu)
      // 1.9 : le podium a eu son temps, le serveur a terminé le dévoilement : place aux jumeaux
      else if (lu.etat === 'devoilee' && d.etat === 'devoilement') { d.etat = 'devoilee'; jumeaux = true }
    } catch { /* coupure passagère */ }
  }
  async function agir(action, extra = {}) {
    gestes++
    if (d?.etat !== 'devoilement') {             // on rejoue une archive : tout se passe ici
      if (action === 'suivant') aller(pas + 1)
      else if (action === 'revenir') aller(pas - 1)
      else if (action === 'aller') aller(extra.pas)
      return
    }
    try { appliquer(await api.post(`/api/soirees/${soiree}/pas`, { action, ...extra })) }
    catch (e) { erreur = e.message }
  }

  // 1.9 : les temps du dévoilement (Réglages) : durée maximum de la remontée, selfie en grand
  let reglages = $state({ duree_revelation: 60, duree_selfie: 6, devoilement_auto: true })
  let attenteFin
  function finRevelation() {
    // l'animation est jouée : 5 s sur « Vainqueur », puis le podium (le serveur l'ignore s'il est déjà passé)
    clearTimeout(attenteFin)
    if (d?.etat !== 'devoilement' || !auto?.actif || auto.pause) return
    const depuis = pas
    attenteFin = setTimeout(() => { if (pas === depuis && auto?.actif && !auto.pause) agir('suivant', { depuis }) }, 5000)
  }
  let finDemandee = false
  $effect(() => {
    // le podium a eu son temps : la télé termine elle-même (le serveur le fait aussi, au prochain « je regarde »)
    if (d?.etat === 'devoilement' && fini && auto?.actif && !enPause && resteMs === 0 && !finDemandee) {
      finDemandee = true
      terminer()
    }
  })

  onMount(async () => {
    mesurer()
    api.get('/api/reglages').then((r) => (reglages = { ...reglages, ...r })).catch(() => {})
    try {
      const lu = await api.get(`/api/soirees/${soiree}/devoilement`)
      d = { ...lu, chansons: lu.chansons.map(normaliser) }
      pas = pasTri = Math.min(d.pas, fin)
      auto = lu.auto || null
      luA = Date.now()
      if (lu.etat === 'devoilement') appliquer(lu)
      charge = true
    } catch (e) { erreur = e.message }
    garderEcran()
  })

  const suivi = setInterval(relire, 1000)
  const horlogeEcran = setInterval(() => (maintenantMs = Date.now()), 100)
  // 1.8 : « je regarde » toutes les 2 s : sans régie devant l'écran, le serveur arrête le défilement (iPhone verrouillé)
  const regard = setInterval(() => {
    if (d?.etat === 'devoilement' && !document.hidden) api.post(`/api/soirees/${soiree}/regard`).catch(() => {})
  }, 2000)
  // 1.8 : l'écran reste allumé pendant le dévoilement (sinon l'iPhone se verrouille et la recopie AirPlay s'arrête)
  let verrou = null
  async function garderEcran() {
    try { if ('wakeLock' in navigator && !document.hidden) verrou = await navigator.wakeLock.request('screen') } catch { /* refusé : tant pis */ }
  }
  function visibilite() {
    if (!document.hidden) { garderEcran(); relire(); if (d?.etat === 'devoilement') api.post(`/api/soirees/${soiree}/regard`).catch(() => {}) }
  }
  onDestroy(() => { clearInterval(suivi); clearInterval(horlogeEcran); clearInterval(regard); clearTimeout(echeance); clearTimeout(attenteFin); try { verrou?.release() } catch { /* rien */ } })

  // Le temps qui reste avant le pays suivant (barre rose sous l'addition)
  let resteMs = $derived(auto?.actif && !auto.pause && auto.prochain_dans !== null ? Math.max(0, auto.prochain_dans - (maintenantMs - luA)) : null)
  let enPause = $derived(!!auto?.actif && auto.pause)
  let avantDernier = $derived(pas === etapes.length - 1)

  function aller(n) {
    n = Math.max(0, Math.min(fin, n))
    // 1.8 : les pays en lice se jouent dès qu'on entre dans le dernier pas depuis un pas plus tôt vu sur cet écran
    // (pas seulement le pas juste avant) ; au chargement ou en revenant du podium : la fin tout de suite.
    animerDernier = charge && n === etapes.length && pas < n && etapes[n - 1]?.phase === 'public'
    clearTimeout(attenteTri)
    if (n === pas + 1 && n <= etapes.length) {
      // un pas en avant : les points s'ajoutent sur place, puis la ligne prend sa nouvelle place
      attenteTri = setTimeout(() => (pasTri = n), RETARD_TRI)
    } else pasTri = n               // retour, « Tout afficher » ou podium : tout de suite
    pas = n
  }
  // 1.6 : « Terminer » ouvre les résultats sur les téléphones (avec les jumeaux de chacun) et passe la télé à
  // l'écran des jumeaux de vote ; « Fermer » y revient à la régie.
  let jumeaux = $state(false)
  async function terminer() {
    try { await api.post(`/api/soirees/${soiree}/terminer`) } catch { /* déjà terminée : on rejoue une archive */ }
    jumeaux = true
  }
  function touche(e) {
    if (e.key === 'ArrowRight' || e.key === ' ') agir('suivant')
    if (e.key === 'ArrowLeft') agir('revenir')
  }
</script>

<svelte:window onresize={mesurer} onkeydown={touche} />
<svelte:document onvisibilitychange={visibilite} />

<div class="fixed inset-0 z-30 bg-background" style="--jury: #7aa2e3; --public: var(--primary)"
     ontouchstart={doigtPose} ontouchend={doigtLeve}>
  {#if erreur}
    <div class="grid h-full place-items-center p-6 text-center">
      <div><p role="alert">{erreur}</p><button class="pastille mt-4" onclick={onferme}>Fermer</button></div>
    </div>
  {:else if d}
    <!-- Toute la surface avance d'un pas ; les trois commandes discrètes sont posées par-dessus -->
    <button class="absolute inset-0 cursor-default" aria-label="Pas suivant" onclick={() => (fini ? null : agir('suivant'))}></button>

    {#if dernierPas}
      {#key pas}
        <div class="pointer-events-none relative h-full px-[max(1rem,env(safe-area-inset-left))] pt-12 pb-[max(0.5rem,env(safe-area-inset-bottom))]">
          <DernierVote chansons={d.chansons} totaux={totauxDernier} dernier={courant.chanson} gain={courant.total}
                       ordre={d.classement.map((l) => l.chanson)} gagnant={d.classement[0]?.chanson} anime={animerDernier}
                       maxMs={reglages.duree_revelation * 1000} onfini={finRevelation} />
        </div>
      {/key}
    {:else}
    <div class="pointer-events-none relative grid h-full gap-x-8 p-[max(1rem,env(safe-area-inset-top))] landscape:grid-cols-[minmax(0,1.15fr)_minmax(0,1fr)]">
      <div class="min-w-0">
        {#if avecJury}
          <p class="legende mb-1 flex gap-4 px-3 text-xs text-muted-foreground"><span><i class="pastille-jury"></i>Jury</span><span><i class="pastille-public"></i>Public</span></p>
        {/if}
        <ol class="classement grid content-start overflow-hidden" aria-label="Classement du groupe" style="--h: {hauteurLigne}px">
          {#each tableau as l, i (l.chanson)}
            <li animate:flip={{ duration: 900, easing: cubicInOut }}
                class="rangee {recu.has(l.chanson) ? 'recu recu-' + teinte : i === 0 && pas > 0 ? 'en-tete' : ''}">
              <span class="rang shrink-0 text-right opacity-60">{l.rang ?? i + 1}</span>
              <span class="drapeau shrink-0">{drapeau(l.c.pays, l.c.code_pays)}</span>
              <span class="min-w-0 flex-1 truncate">{l.c.pays}</span>
              <span class="total chiffre shrink-0 text-right"><Compteur valeur={l.total} retard={recu.has(l.chanson) ? 250 : 0} /></span>
              {#if avecJury}
                <span class="barre" aria-hidden="true">
                  <i style="width: {(l.jury / plus) * 100}%; background: var(--jury)"></i><i style="width: {(l.pub / plus) * 100}%; background: var(--public)"></i>
                </span>
              {/if}
            </li>
          {/each}
        </ol>
      </div>

      <div class="grid min-w-0 content-center justify-items-center overflow-hidden pt-14 text-center portrait:hidden">
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
          <!-- 1.8 : le bouton des jumeaux sous le podium (avant : en haut à droite) -->
          <button class="bouton-jumeaux pointer-events-auto mt-4" onclick={terminer}>Voir les jumeaux de vote</button>
          <p class="mt-1.5 text-xs text-muted-foreground">Termine la soirée et ouvre les résultats sur les téléphones.</p>
        {:else}
          {#key pas}
            {#if courant.phase === 'top'}
              <div class="w-full min-w-0" in:fade={{ duration: 250 }}>
                <p class="text-lg font-light" style="color: var(--jury)">Les points du jury : le top 5</p>
                <ol class="top mx-auto mt-3" aria-label="Top 5 du jury">
                  {#each courant.top as t, i (t.chanson)}
                    {@const c = chansons[t.chanson]}
                    <!-- du cinquième au premier, l'un après l'autre -->
                    <li class:premier={i === 0} style="animation-delay: {(courant.top.length - 1 - i) * 0.45}s">
                      <span class="chiffre rang">{i + 1}</span>
                      <span class="shrink-0">{drapeau(c.pays, c.code_pays)}</span>
                      <span class="min-w-0 flex-1 truncate text-left">{c.pays}</span>
                      <span class="chiffre points">{t.points}</span>
                    </li>
                  {/each}
                </ol>
                <p class="mt-3 text-sm text-muted-foreground">Puis le public, chanson par chanson.</p>
              </div>
            {:else if courant.phase}
              {@const c = chansons[courant.chanson]}
              <div class="w-full min-w-0" in:fade={{ duration: 200 }}>
                <p class="text-lg font-light" style="color: var(--{courant.phase})">{courant.phase === 'jury' ? 'Les points du jury' : 'Les points du public'}</p>
                <p class="mt-1 truncate font-light tracking-tight" style="font-size: clamp(1.3rem, 7vh, 2.6rem); line-height: 1.15">{drapeau(c.pays, c.code_pays)} {c.pays}</p>
                {#if c.artiste || c.titre}<p class="truncate text-sm text-muted-foreground">{c.artiste}{c.titre ? ' – ' + c.titre : ''}</p>{/if}
                {#if courant.phase === 'jury'}
                  <p class="chiffre mt-1" style="font-size: 18vh; line-height: 1.05; color: var(--jury)" in:scale={{ start: 0.7, duration: 350 }}>{courant.total}</p>
                  <p class="text-base text-muted-foreground">{courant.total > 1 ? 'points' : 'point'}</p>
                  {#if courant.lot.length}
                    <p class="mx-auto mt-1 line-clamp-1 max-w-md text-sm text-muted-foreground">{[...courant.lot].sort((x, y) => y.points - x.points).map((p) => `${p.points} de ${p.prenom}`).join(', ')}</p>
                  {/if}
                {:else}
                  <!-- les points du public s'ajoutent à ceux du jury : 14 + 9 = 23 -->
                  <p class="addition mt-2" aria-label="{courant.avant} points du jury, plus {courant.total} du public">
                    <span style="color: var(--jury)">{courant.avant}</span><span class="signe">+</span><span class="arrive" style="color: var(--public)">{courant.total}</span>
                  </p>
                  <p class="chiffre" style="font-size: 16vh; line-height: 1.05"><Compteur valeur={courant.avant + courant.total} depart={courant.avant} retard={450} duree={1000} /></p>
                  <p class="text-base text-muted-foreground">points en tout</p>
                  {#if auto?.actif}
                    <!-- 1.8 : le temps avant le pays suivant -->
                    <div class="temps mx-auto mt-3" role="timer" aria-label={enPause ? 'Défilement en pause' : `Pays suivant dans ${Math.ceil((resteMs ?? 0) / 1000)} secondes`}>
                      <span class="barre-temps"><i style="width: {enPause ? 0 : 100 - ((resteMs ?? 0) / auto.duree) * 100}%"></i></span>
                      <span class="text-sm text-muted-foreground">{enPause ? 'En pause' : `${avantDernier ? 'Le dernier vote du public' : 'Pays suivant'} dans ${Math.max(1, Math.ceil((resteMs ?? 0) / 1000))} s`}</span>
                    </div>
                  {/if}
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
                <p class="chiffre mt-1 text-primary" style="font-size: 18vh; line-height: 1.05" in:scale={{ start: 0.7, duration: 350 }}>{courant.annonce.points}</p>
                <p class="text-lg text-muted-foreground">{courant.annonce.points === 12 ? 'Douze points' : 'points'}</p>
                <p class="mt-1 max-w-full truncate font-light tracking-tight" style="font-size: clamp(1.3rem, 7vh, 2.6rem); line-height: 1.15">{drapeau(c.pays, c.code_pays)} {c.pays}</p>
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

    {/if}

    {#if fini}
      <div class="cotillons" aria-hidden="true">
        {#each cotillons as k}
          <i style="left: {k.gauche}%; width: {k.largeur}px; height: {k.rond ? k.largeur : k.largeur * 1.8}px; background: {k.couleur}; border-radius: {k.rond ? '50%' : '1px'}; animation-duration: {k.duree}s; animation-delay: {k.retard}s; --tourne: {k.tourne}deg"></i>
        {/each}
      </div>
    {/if}

    <div class="absolute inset-x-0 top-[max(0.5rem,env(safe-area-inset-top))] flex justify-end gap-2 px-4 text-xs">
      <p class="mr-auto self-center text-muted-foreground landscape:hidden">Tourne le téléphone en paysage.</p>
      <p class="geste mr-auto hidden self-center text-muted-foreground portrait:hidden">Glisse vers la droite pour sortir</p>
      {#if auto?.actif && courant?.phase !== 'public'}
        <!-- 1.9 : les autres étapes passent seules aussi : le temps qui reste, discret -->
        <p class="mr-auto self-center text-muted-foreground" role="timer">{enPause ? 'En pause' : `Suite dans ${Math.max(1, Math.ceil((resteMs ?? 0) / 1000))} s`}</p>
      {/if}
      {#if pas > 0}<button class="commande" onclick={() => agir('revenir')}>Revenir</button>{/if}
      {#if auto?.actif}<button class="commande" onclick={() => agir(enPause ? 'reprendre' : 'pause')}>{enPause ? 'Reprendre' : 'Pause'}</button>{/if}
      {#if !fini}<button class="commande" onclick={() => agir('aller', { pas: fin })}>Tout afficher</button>{/if}
      {#if !fini}<button class="commande" onclick={onferme}>Fermer</button>{/if}
    </div>
  {/if}
</div>
{#if jumeaux}<EcranJumeaux {soiree} {onferme} dureeSelfie={reglages.duree_selfie} />{/if}

<style>
  /* La hauteur d'une ligne (--h) dépend du nombre de chansons et de la hauteur de l'écran ; le texte suit. */
  .classement { gap: min(4px, calc(var(--h) * 0.08)); }
  .rangee { position: relative; display: flex; height: var(--h); align-items: center; gap: calc(var(--h) * 0.25); overflow: hidden;
    border-radius: min(0.5rem, calc(var(--h) * 0.2)); padding: 0 min(0.75rem, calc(var(--h) * 0.3)); font-size: clamp(5px, calc(var(--h) * 0.44), 1.25rem); background: var(--background);
    transition: background-color 0.5s, box-shadow 0.5s; }
  .rangee.en-tete { background: var(--card); }
  .rangee.recu { z-index: 1; }
  .rangee.recu-jury { background: color-mix(in oklab, var(--jury) 30%, var(--background)); box-shadow: inset 4px 0 0 var(--jury); }
  .rangee.recu-public { background: color-mix(in oklab, var(--public) 30%, var(--background)); box-shadow: inset 4px 0 0 var(--public); }
  .rangee .rang { width: 1.4em; font-size: 0.75em; }
  .rangee .drapeau { font-size: 1.15em; line-height: 1; }
  .rangee .total { width: 2.6em; font-size: 1.25em; }
  @media (pointer: coarse) { .geste { display: block; } }
  .barre { position: absolute; left: 0.75rem; right: 0.75rem; bottom: 0; display: flex; height: 3px; overflow: hidden; border-radius: 2px; opacity: 0.9; }
  .barre i { display: block; height: 100%; transition: width 0.9s cubic-bezier(0.2, 0.8, 0.2, 1); }
  .legende i { display: inline-block; width: 0.6rem; height: 0.6rem; margin-right: 0.35rem; border-radius: 999px; vertical-align: -1px; }
  .pastille-jury { background: var(--jury); }
  .pastille-public { background: var(--public); }
  .addition { display: flex; align-items: baseline; justify-content: center; gap: 0.6rem; font-size: 7vh; font-weight: 300; line-height: 1; font-variant-numeric: tabular-nums; }
  .addition .signe { color: var(--muted-foreground); }
  .addition .arrive { animation: arriver 0.5s cubic-bezier(0.2, 0.8, 0.2, 1) 0.15s both; }
  @keyframes arriver { from { opacity: 0; transform: translateY(-2vh) scale(1.3); } to { opacity: 1; transform: none; } }

  .top { display: grid; max-width: 26rem; gap: 0.4rem; }
  .top li { display: flex; align-items: center; gap: 0.7rem; border-radius: 0.6rem; padding: 0.35rem 0.8rem; font-size: clamp(1rem, 4.6vh, 1.6rem);
    background: color-mix(in oklab, var(--jury) 14%, var(--background)); animation: entrer-top 0.55s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .top li.premier { background: color-mix(in oklab, var(--jury) 38%, var(--background)); box-shadow: inset 4px 0 0 var(--jury); }
  .top .rang { width: 1.4rem; text-align: right; color: var(--muted-foreground); }
  .top .points { color: var(--jury); }
  .top li.premier .points { color: #fff; }
  @keyframes entrer-top { from { opacity: 0; transform: translateX(3rem); } to { opacity: 1; transform: none; } }

  .commande { min-height: 2.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--background); padding: 0 1rem; color: var(--muted-foreground); }
  .commande.plein { background: var(--primary); color: var(--primary-foreground); border-color: var(--primary); }
  .bouton-jumeaux { min-height: 3.2rem; border-radius: 999px; background: var(--primary); color: var(--primary-foreground); padding: 0 1.8rem;
    font-size: clamp(1rem, 3.4vh, 1.3rem); font-weight: 600; }
  .bouton-jumeaux:focus-visible { outline: 3px solid var(--foreground); outline-offset: 3px; }
  .temps { display: grid; width: min(22rem, 90%); gap: 0.4rem; justify-items: center; }
  .barre-temps { display: block; width: 100%; height: 6px; overflow: hidden; border-radius: 3px; background: var(--muted); }
  .barre-temps i { display: block; height: 100%; background: var(--public); transition: width 0.1s linear; }

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
    .marche, .addition .arrive, .top li { animation: none; }
  }
</style>
