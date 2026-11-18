<script>
  // « Réglages » : ce qui n'est pas un service. Toujours en bas : la version et la déconnexion.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'
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
    charges = true
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
  const NOMS = { pas_note: 'Pas de la note', ha_webhook: 'Webhook de Home Assistant' }
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
  onMount(() => lire().catch((e) => (erreur = e.message)))

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
