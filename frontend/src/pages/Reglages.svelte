<script>
  // « Réglages » : ce qui n'est pas un service. Toujours en bas : la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import * as sons from '$lib/sons.js'
  import { PAYS, drapeau } from '$lib/pays.js'
  let { session, deconnecter } = $props()

  let concours = $state([])
  let invites = $state([])
  let nom = $state('')
  let erreur = $state('')

  async function lire() {
    concours = (await api.get('/api/concours')).filter((c) => c.actif)
    invites = (await api.get('/api/invites')).filter((i) => i.actif)
    prendre(await api.get('/api/reglages'))
  }
  let pasNote = $state(0.5)
  let webhook = $state('')
  let webhookMessage = $state('')
  let webhookErreur = $state('')
  let charges = $state(false)      // le champ attend les réglages lus avant d'être modifiable
  function prendre(r) {
    pasNote = r.pas_note
    webhook = r.ha_webhook ?? ''
    for (const e of ETAPES) temps[e.cle] = r[e.cle] ?? temps[e.cle]
    auto = r.devoilement_auto ?? true
    sonsActifs = r.sons ?? true
    volumeSons = r.volume_sons ?? 70
    notrePays = r.notre_pays ?? 'FR'
    sons.regler(r)
    charges = true
  }
  // 1.12 : notre pays, noté et classé mais sans points (vide : aucun)
  let notrePays = $state('FR')
  let paysErreur = $state('')
  async function reglerPays(v) {
    paysErreur = ''
    try { prendre(await api.put('/api/reglages', { notre_pays: v })) } catch (x) { paysErreur = x.message; prendre(await api.get('/api/reglages')) }
  }
  // 1.11.0 : les sons sur la télé : oui / non, un volume, et chaque son remplaçable par un fichier
  let sonsActifs = $state(true)
  let volumeSons = $state(70)
  let listeSons = $state([])
  let sonsMessage = $state('')
  let enCours = $state('')          // le son dont un fichier part
  async function lireSons() { try { listeSons = await api.get('/api/sons') } catch (x) { sonsMessage = x.message } }
  async function reglerSons(corps) {
    sonsMessage = ''
    try { prendre(await api.put('/api/reglages', corps)) } catch (x) { sonsMessage = x.message; prendre(await api.get('/api/reglages')) }
  }
  async function remplacer(nom, ev) {
    const fichier = ev.currentTarget.files?.[0]
    ev.currentTarget.value = ''
    if (!fichier) return
    sonsMessage = ''
    if (fichier.size > 5 * 1024 * 1024) { sonsMessage = 'Fichier trop lourd : 5 Mo au plus.'; return }
    enCours = nom
    try {
      const octets = await fichier.arrayBuffer()
      try { await sons.decoder(octets) }          // avis du conseil : un fichier illisible ici est refusé avant l'envoi
      catch { throw new Error(`« ${fichier.name} » ne se lit pas dans ce navigateur : rien n'est envoyé.`) }
      const r = await fetch(`/api/sons/${nom}`, { method: 'PUT', credentials: 'same-origin', body: octets,
        headers: { 'Content-Type': fichier.type || 'application/octet-stream' } })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || `Le serveur a répondu ${r.status}.`)
      sons.oublier(nom)
      await sons.chargerFichiers()
      sonsMessage = `${sons.LIBELLES[nom]} : remplacé par « ${fichier.name} ».`
      await lireSons()
    } catch (x) { sonsMessage = x.message } finally { enCours = '' }
  }
  async function revenir(nom) {
    sonsMessage = ''
    try {
      const r = await fetch(`/api/sons/${nom}`, { method: 'DELETE', credentials: 'same-origin' })
      if (!r.ok) throw new Error(`Le serveur a répondu ${r.status}.`)
      sons.oublier(nom)
      await sons.chargerFichiers()
      sonsMessage = `${sons.LIBELLES[nom]} : de nouveau le son de l'appli.`
      await lireSons()
    } catch (x) { sonsMessage = x.message }
  }
  // 1.9 : le dévoilement, manuel (tout au toucher) ou automatique, et le temps de chaque étape (choix de Julien)
  const ETAPES = [
    { cle: 'duree_depart', nom: 'Départ', aide: 'de l\'écran d\'attente au top 5 du jury', min: 2, max: 600 },
    { cle: 'duree_jury', nom: 'Jury', aide: 'le top 5, tous les points du jury d\'un coup', min: 2, max: 600 },
    { cle: 'duree_public', nom: 'Public', aide: 'chaque pays, jusqu\'à l\'avant-dernier', min: 2, max: 120 },
    { cle: 'duree_revelation', nom: 'Révélation', aide: 'durée maximum de la remontée du dernier pays', min: 5, max: 300 },
    { cle: 'duree_podium', nom: 'Podium', aide: 'puis l\'écran des jumeaux', min: 2, max: 600 },
    { cle: 'duree_selfie', nom: 'Selfie d\'un duo en grand', aide: 'avant qu\'il se range dans sa carte', min: 2, max: 60 },
    { cle: 'duree_mode_emploi', nom: 'Mode d\'emploi sur la télé', aide: 'quand tout le monde est là', min: 5, max: 600 },
  ]
  let auto = $state(true)
  let temps = $state({ duree_depart: 10, duree_jury: 15, duree_public: 5, duree_revelation: 60, duree_podium: 15, duree_selfie: 6, duree_mode_emploi: 30 })
  let tempsMessage = $state('')
  async function reglerAuto(v) {
    erreur = ''
    try { prendre(await api.put('/api/reglages', { devoilement_auto: v })) } catch (x) { erreur = x.message }
  }
  async function reglerTemps(cle) {
    tempsMessage = ''
    const v = Number(temps[cle])
    try { prendre(await api.put('/api/reglages', { [cle]: v })); tempsMessage = 'Enregistré.' }
    catch (x) { tempsMessage = x.message; prendre(await api.get('/api/reglages')) }
  }
  // 1.5 : reprise de toutes les soirées dévoilées vers carnet (fiche et coffre Contacts)
  let carnetMessage = $state('')
  async function envoyerCarnet() {
    carnetMessage = 'Envoi…'
    try {
      const r = await api.post('/api/carnet/envoyer', {})
      carnetMessage = `${r.envoyees} soirée(s) sur ${r.soirees} reçue(s) par carnet` + (r.en_attente ? ` ; ${r.en_attente} en attente (carnet injoignable ou trop ancien).` : '.')
    } catch (err) { carnetMessage = err.message }
  }
  async function reglerPas(v) {
    erreur = ''
    try { prendre(await api.put('/api/reglages', { pas_note: v })) } catch (x) { erreur = x.message }
  }
  async function enregistrerWebhook(e) {
    e.preventDefault()
    webhookMessage = ''
    webhookErreur = ''
    try {
      prendre(await api.put('/api/reglages', { ha_webhook: webhook }))
      webhookMessage = webhook ? 'Adresse enregistrée (rien n\'est encore envoyé).' : 'Adresse effacée : pas de notification.'
    } catch (x) { webhookErreur = x.message }
  }

  // 1.2 : restaurer les réglages depuis une sauvegarde gardée par l'Anneau (réglages seulement)
  const NOMS = { pas_note: 'Pas de la note', ha_webhook: 'Webhook de Home Assistant', devoilement_auto: 'Dévoilement automatique',
    duree_depart: 'Temps du départ', duree_jury: 'Temps du jury', duree_public: 'Temps par pays du public',
    duree_revelation: 'Durée maximum de la révélation', duree_podium: 'Temps du podium', duree_selfie: 'Selfie en grand',
    duree_mode_emploi: 'Mode d\'emploi sur la télé', sons: 'Sons sur la télé', volume_sons: 'Volume des sons',
    notre_pays: 'Notre pays' }
  const PAS = { 1: 'au point', 0.5: 'au demi-point', 0.25: 'au quart de point' }
  const montrer = (cle, v) => (cle === 'pas_note' ? (PAS[v] ?? String(v)) : v === '' || v == null ? '(vide)' : String(v))
  let dates = $state([])
  let jour = $state('')
  let ecarts = $state(null)
  let versionSauvee = $state('')
  let restaurerMessage = $state('')
  let restaurerErreur = $state('')
  let restaurerAttente = $state(false)
  async function voirSauvegardes() {
    restaurerMessage = ''
    restaurerErreur = ''
    ecarts = null
    restaurerAttente = true
    try {
      dates = (await api.get('/api/restaurer')).dates
      jour = dates[0] ?? ''
      if (jour) await voirEcarts()
    } catch (x) { dates = []; restaurerErreur = x.message } finally { restaurerAttente = false }
  }
  async function voirEcarts() {
    restaurerMessage = ''
    restaurerErreur = ''
    ecarts = null
    if (!jour) return
    try {
      const r = await api.get('/api/restaurer?le=' + encodeURIComponent(jour))
      ecarts = r.differences
      versionSauvee = r.version
    } catch (x) { restaurerErreur = x.message }
  }
  async function restaurer() {
    restaurerErreur = ''
    restaurerAttente = true
    try {
      const r = await api.post('/api/restaurer', { le: jour })
      prendre(r.reglages)
      restaurerMessage = r.restaures.length
        ? `Réglages du ${jour} restaurés : ${r.restaures.map((c) => NOMS[c] ?? c).join(', ')}.`
        : 'Rien à changer : les réglages sont déjà ceux de cette sauvegarde.'
      ecarts = []
    } catch (x) { restaurerErreur = x.message } finally { restaurerAttente = false }
  }
  async function regler(invite, corps) {
    erreur = ''
    try { await api.put('/api/invites/' + invite.id, corps); await lire() } catch (x) { erreur = x.message }
  }
  onMount(() => { lire().catch((e) => (erreur = e.message)); lireSons() })

  async function ajouter(e) {
    e.preventDefault()
    erreur = ''
    try { await api.post('/api/concours', { nom }); nom = ''; await lire() } catch (x) { erreur = x.message }
  }
  async function retirer(c) {
    erreur = ''
    try {
      const r = await fetch('/api/concours/' + c.id, { method: 'DELETE', credentials: 'same-origin' })
      if (!r.ok) throw new Error((await r.json().catch(() => null))?.detail || 'Le concours n\'a pas pu être retiré.')
      await lire()
    } catch (x) { erreur = x.message }
  }
</script>

<header class="mb-5">
  <h1 class="titre">Réglages</h1>
</header>

<section class="rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Concours</h2>
  <p class="mt-1 text-sm text-muted-foreground">La liste proposée quand tu crées une soirée. Retirer un concours ne touche pas aux soirées déjà faites.</p>
  {#if erreur}<p class="mt-2 text-sm text-destructive" role="alert">{erreur}</p>{/if}
  <ul class="mt-3 grid gap-2" aria-label="Concours">
    {#each concours as c (c.id)}
      <li class="flex items-center gap-3 rounded-xl border px-3 py-2">
        <span class="font-medium">{c.nom}</span>
        <span class="mr-auto text-sm text-muted-foreground">{c.soirees ? `${c.soirees} soirée${c.soirees > 1 ? 's' : ''}` : ''}</span>
        <Button variant="outline" size="sm" onclick={() => retirer(c)} aria-label="Retirer {c.nom}" disabled={concours.length === 1}>Retirer</Button>
      </li>
    {/each}
  </ul>
  <form class="mt-4 flex gap-2" onsubmit={ajouter}>
    <input class="saisie flex-1" bind:value={nom} placeholder="Nom du concours" maxlength="60" aria-label="Nom d'un nouveau concours" required />
    <Button type="submit">Ajouter</Button>
  </form>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Pas de la note</h2>
  <p class="text-sm text-muted-foreground">Les invités notent de 0 à 20. Les notes déjà données restent telles quelles.</p>
  <div class="mt-3 flex flex-wrap gap-2" role="group" aria-label="Pas de la note">
    {#each [[1, 'Au point (12, 13…)'], [0.5, 'Au demi-point (12,5)'], [0.25, 'Au quart de point (12,25)']] as [v, nom]}
      <button class="pastille" aria-pressed={pasNote === v} onclick={() => reglerPas(v)}>{nom}</button>
    {/each}
  </div>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Notre pays">
  <h2 class="text-lg font-semibold">Notre pays</h2>
  <p class="text-sm text-muted-foreground">Comme au concours, on ne vote pas pour son propre pays. Les invités le notent, le commentent et le classent, mais il ne reçoit aucun point : ses points vont à la chanson suivante de leur classement. Le réglage compte pour les soirées pas encore dévoilées.</p>
  <label class="mt-3 block text-sm">
    <span class="sr-only">Notre pays</span>
    <select class="champ-select" value={notrePays} disabled={!charges} onchange={(ev) => reglerPays(ev.currentTarget.value)}>
      <option value="">Aucun : tous les pays reçoivent des points</option>
      {#each PAYS as p (p.code)}<option value={p.code}>{drapeau('', p.code)} {p.nom}</option>{/each}
    </select>
  </label>
  {#if paysErreur}<p class="mt-2 text-sm text-destructive" role="alert">{paysErreur}</p>{/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Dévoilement">
  <h2 class="text-lg font-semibold">Dévoilement</h2>
  <p class="mt-1 text-sm text-muted-foreground">En automatique, chaque étape passe seule ; l'hôte garde Pause, Revenir et Suivant. En manuel, tout se fait au toucher.</p>
  <div class="mt-3 flex flex-wrap gap-2" role="group" aria-label="Manuel ou automatique">
    <button class="pastille" aria-pressed={!auto} disabled={!charges} onclick={() => reglerAuto(false)}>Manuel</button>
    <button class="pastille" aria-pressed={auto} disabled={!charges} onclick={() => reglerAuto(true)}>Automatique</button>
  </div>
  <div class="mt-4 grid gap-2 sm:grid-cols-2">
    {#each ETAPES as e (e.cle)}
      <label class="flex items-center gap-3 rounded-xl border px-3 py-2">
        <span class="min-w-0 flex-1"><span class="block text-sm font-medium">{e.nom}</span><span class="block text-xs text-muted-foreground">{e.aide}</span></span>
        <input type="number" inputmode="numeric" min={e.min} max={e.max} step="1" class="w-20 rounded-lg border bg-background px-2 py-2 text-right"
               bind:value={temps[e.cle]} onchange={() => reglerTemps(e.cle)} disabled={!charges} aria-label="{e.nom}, en secondes" />
        <span class="text-sm text-muted-foreground">s</span>
      </label>
    {/each}
  </div>
  {#if tempsMessage}<p class="mt-2 text-sm text-muted-foreground" role="status">{tempsMessage}</p>{/if}

  <!-- 1.11.0 : les sons, joués par la télé seulement (les téléphones des invités restent muets) -->
  <div class="mt-5 border-t pt-4" role="group" aria-label="Sons">
    <div class="flex flex-wrap items-center gap-3">
      <h3 class="mr-auto font-semibold">Sons sur la télé</h3>
      <button class="interrupteur" role="switch" aria-checked={sonsActifs} aria-label="Sons sur la télé" disabled={!charges}
              onclick={() => reglerSons({ sons: !sonsActifs })}><i></i></button>
    </div>
    <p class="mt-1 text-sm text-muted-foreground">Fabriqués par l'appli ; chacun peut être remplacé par un fichier (mp3, m4a, ogg ou wav, 5 Mo au plus). La télé a aussi son bouton haut-parleur pour couper d'un geste.</p>
    <label class="mt-3 flex items-center gap-3 text-sm">
      <span class="w-16 shrink-0">Volume</span>
      <input type="range" min="0" max="100" step="5" class="min-w-0 flex-1" bind:value={volumeSons} disabled={!charges || !sonsActifs}
             onchange={() => reglerSons({ volume_sons: Number(volumeSons) })} aria-label="Volume des sons" />
      <span class="chiffre w-10 text-right">{volumeSons}</span>
    </label>
    <ul class="mt-3 grid gap-2" aria-label="Les sons">
      {#each listeSons as s (s.nom)}
        <li class="flex flex-wrap items-center gap-2 rounded-xl border px-3 py-2">
          <span class="min-w-0 flex-1 basis-48"><span class="block text-sm font-medium">{sons.LIBELLES[s.nom] ?? s.nom}</span>
            <span class="block text-xs text-muted-foreground">{s.fichier ? `Fichier de l'hôte (${Math.max(1, Math.round(s.taille / 1024))} Ko)` : 'Son de l\'appli'}</span></span>
          <Button variant="outline" size="sm" onclick={() => sons.ecouterSon(s.nom)} aria-label="Écouter : {sons.LIBELLES[s.nom]}">Écouter</Button>
          <label class="remplacer">
            <input type="file" accept="audio/mpeg,audio/mp4,audio/x-m4a,audio/ogg,audio/wav,audio/x-wav,.mp3,.m4a,.ogg,.wav" class="sr-only"
                   aria-label="Remplacer par un fichier : {sons.LIBELLES[s.nom]}" disabled={!!enCours} onchange={(ev) => remplacer(s.nom, ev)} />
            <span>{enCours === s.nom ? 'Envoi…' : 'Remplacer par un fichier'}</span>
          </label>
          {#if s.fichier}<Button variant="outline" size="sm" onclick={() => revenir(s.nom)} aria-label="Revenir au son de l'appli : {sons.LIBELLES[s.nom]}">Revenir au son de l'appli</Button>{/if}
        </li>
      {/each}
    </ul>
    {#if sonsMessage}<p class="mt-2 text-sm text-muted-foreground" role="status">{sonsMessage}</p>{/if}
  </div>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5" aria-label="Envoi vers carnet">
  <h2 class="text-lg font-semibold">Envoi vers carnet</h2>
  <p class="mt-1 text-sm text-muted-foreground">Quand tu clôtures la soirée (À traiter), elle part à carnet : note moyenne, classement et podium de chaque invité, rangés sur sa fiche et dans le coffre Contacts. Un envoi raté est réessayé toutes les 10 minutes. Le bouton renvoie toutes les soirées clôturées.</p>
  <div class="mt-3 flex flex-wrap items-center gap-3">
    <Button variant="outline" onclick={envoyerCarnet}>Renvoyer les soirées clôturées à carnet</Button>
    {#if carnetMessage}<span class="text-sm text-muted-foreground" role="status">{carnetMessage}</span>{/if}
  </div>
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Notification Home Assistant <span class="text-sm font-normal text-muted-foreground">(pas encore active)</span></h2>
  <p class="mt-1 text-sm text-muted-foreground">Pas encore branchée : rien n'est envoyé à Home Assistant. L'adresse du webhook est gardée pour le jour où elle le sera (prévenir ton téléphone quand tous les invités ont envoyé). En attendant, c'est la régie qui montre que tout le monde a envoyé. L'adresse n'est jamais copiée dans les sauvegardes.</p>
  <form class="mt-3 flex flex-wrap gap-2" onsubmit={enregistrerWebhook}>
    <input class="saisie min-w-0 flex-1" type="text" inputmode="url" bind:value={webhook} placeholder="http://…/api/webhook/…" maxlength="300"
      aria-label="Adresse du webhook de Home Assistant" autocomplete="off" spellcheck="false" disabled={!charges} />
    <Button type="submit" disabled={!charges}>Enregistrer</Button>
  </form>
  {#if webhookErreur}<p class="mt-2 text-sm text-destructive" role="alert">{webhookErreur}</p>{/if}
  {#if webhookMessage}<p class="mt-2 text-sm text-muted-foreground" role="status">{webhookMessage}</p>{/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Restaurer les réglages</h2>
  <p class="mt-1 text-sm text-muted-foreground">L'Anneau garde chaque nuit une copie des réglages de Douze points (pas de la note). Choisis un jour, regarde ce qui changerait, puis confirme. Les soirées, les invités et les notes ne bougent pas.</p>
  <div class="mt-3 flex flex-wrap items-center gap-2">
    <Button variant="outline" onclick={voirSauvegardes} disabled={restaurerAttente}>Voir les sauvegardes</Button>
    {#if dates.length}
      <select class="saisie min-w-0" bind:value={jour} onchange={voirEcarts} aria-label="Date de la sauvegarde">
        {#each dates as d}<option value={d}>{d}</option>{/each}
      </select>
    {/if}
  </div>
  {#if restaurerErreur}<p class="mt-2 text-sm text-destructive" role="alert">{restaurerErreur}</p>{/if}
  {#if ecarts}
    {#if ecarts.length}
      <ul class="mt-3 grid gap-2" aria-label="Différences avec la sauvegarde">
        {#each ecarts as d (d.cle)}
          <li class="flex flex-wrap items-baseline gap-x-2 rounded-xl border px-3 py-2 text-sm">
            <span class="font-medium">{NOMS[d.cle] ?? d.cle}</span>
            <span class="text-muted-foreground">{montrer(d.cle, d.actuel)} → <span class="text-foreground">{montrer(d.cle, d.sauve)}</span></span>
          </li>
        {/each}
      </ul>
      <div class="mt-3 flex flex-wrap items-center gap-3">
        <Button onclick={restaurer} disabled={restaurerAttente}>Restaurer ces réglages</Button>
        {#if versionSauvee}<span class="text-sm text-muted-foreground">sauvegardés par la version {versionSauvee}</span>{/if}
      </div>
    {:else if !restaurerMessage}
      <p class="mt-3 text-sm text-muted-foreground">Rien à changer : les réglages sont déjà ceux du {jour}.</p>
    {/if}
  {/if}
  {#if restaurerMessage}<p class="mt-2 text-sm text-muted-foreground" role="status">{restaurerMessage}</p>{/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Invités : jury ou public</h2>
  <p class="mt-1 text-sm text-muted-foreground">Coche les membres du jury ; les autres sont le public. Au dévoilement « jury puis public », les points du jury arrivent d'abord, chanson par chanson, puis ceux du public en partant du bas du classement. Tous les points comptent pareil.</p>
  {#if invites.length}
    <ul class="mt-3 grid gap-2 sm:grid-cols-2" aria-label="Invités">
      {#each invites as i (i.id)}
        <li class="flex items-center gap-2 rounded-xl border px-3 py-2">
          <span class="mr-auto font-medium">{i.prenom}</span>
          <button class="pastille" aria-pressed={i.jury} aria-label="{i.prenom} : jury" onclick={() => regler(i, { jury: true })}>Jury</button>
          <button class="pastille" aria-pressed={!i.jury} aria-label="{i.prenom} : public" onclick={() => regler(i, { jury: false })}>Public</button>
          <Button variant="outline" size="sm" onclick={() => regler(i, { actif: false })} aria-label="Retirer {i.prenom} de la liste">Retirer</Button>
        </li>
      {/each}
    </ul>
  {:else}
    <p class="mt-3 text-sm text-muted-foreground">Aucun invité pour l'instant : ils s'ajoutent en préparant une soirée.</p>
  {/if}
</section>

<section class="mt-4 rounded-2xl border bg-card p-5">
  <h2 class="text-lg font-semibold">Adresse donnée aux invités</h2>
  <p class="mt-1 text-sm text-muted-foreground">
    {#if session.adresse}
      Le QR code et le lien mènent à <span class="text-foreground">{session.adresse}</span>. Ils ne répondent que sur le Wi-Fi de la maison.
    {:else}
      Aucune adresse n'est réglée : sans elle, pas de QR code ni de lien. Elle vient de l'Anneau : tuile « Douze points », adresse locale. Si l'Anneau ne répond pas, il n'y a pas de QR code.
    {/if}
  </p>
</section>

<p class="mt-6 flex items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Douze points {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>

<style>
  /* 1.11.0 : l'interrupteur « Sons sur la télé » et le bouton « Remplacer par un fichier » */
  .interrupteur { position: relative; width: 3.25rem; height: 1.9rem; flex-shrink: 0; border-radius: 999px; background: var(--muted);
    border: 1px solid var(--border); transition: background-color 0.2s; }
  .interrupteur i { position: absolute; top: 0.2rem; left: 0.2rem; width: 1.4rem; height: 1.4rem; border-radius: 999px;
    background: var(--foreground); transition: transform 0.2s; }
  .interrupteur[aria-checked="true"] { background: var(--primary); border-color: var(--primary); }
  .interrupteur[aria-checked="true"] i { transform: translateX(1.35rem); background: var(--primary-foreground); }
  .interrupteur:focus-visible, .remplacer:focus-within { outline: 3px solid color-mix(in oklab, var(--primary) 55%, transparent); outline-offset: 2px; }
  .remplacer { display: inline-flex; min-height: 2rem; align-items: center; border-radius: 0.5rem; border: 1px solid var(--border);
    padding: 0 0.75rem; font-size: 0.875rem; cursor: pointer; }
  @media (prefers-reduced-motion: reduce) { .interrupteur, .interrupteur i { transition: none; } }
  .champ-select { width: 100%; max-width: 22rem; min-height: 2.75rem; border-radius: 0.6rem; border: 1px solid var(--border); background: var(--background); padding: 0 0.75rem; color: var(--foreground); }
</style>
