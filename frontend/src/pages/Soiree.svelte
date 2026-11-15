<script>
  // L'écran de travail de l'hôte : préparer la soirée, l'ouvrir, suivre qui a envoyé, dévoiler.
  // Aucune note ni aucun classement n'y apparaît avant le dévoilement : l'hôte note lui aussi.
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  import { drapeau, EMISSIONS, titreEvenement } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Accueil from './Accueil.svelte'
  import Devoilement from './Devoilement.svelte'
  import Images from './Images.svelte'
  let { ondeconnecte } = $props()

  let soirees = $state(null)      // toutes, la plus récente d'abord
  let s = $state(null)            // la soirée en cours de travail (non archivée la plus récente)
  let invites = $state([])
  let concours = $state([])       // la liste réglée dans Réglages
  let erreur = $state('')
  let accueil = $state(false)
  let rejouer = $state(null)      // id d'une soirée dont on (re)joue le dévoilement
  let forcer = $state(null)       // aperçu de ce que « forcer » ferait
  let mode = $state('court')
  let collage = $state('')
  let prenom = $state('')
  let nouvelle = $state({ concours: 'Eurovision', annee: new Date().getFullYear(), emission: 'finale', ville: '' })
  // Le titre se fabrique tout seul (concours, ville, année, émission) tant que l'hôte n'écrit pas le sien.
  let titreEcrit = $state(null)
  let titre = $derived(titreEcrit ?? titreEvenement(nouvelle))
  let minuterie

  async function essayer(action) {
    erreur = ''
    try { return await action() } catch (e) {
      if (e.statut === 401) ondeconnecte()
      else erreur = e.message
    }
  }

  async function lire() {
    await essayer(async () => {
      soirees = await api.get('/api/soirees')
      const courante = soirees.find((x) => x.etat !== 'archivee')
      s = courante ? await api.get('/api/soirees/' + courante.id) : null
      if (s?.etat === 'brouillon') invites = await api.get('/api/invites')
      if (!s) {
        concours = (await api.get('/api/concours')).filter((c) => c.actif).map((c) => c.nom)
        if (!concours.includes(nouvelle.concours)) nouvelle.concours = concours[0]
      }
    })
  }

  onMount(async () => {
    await lire()
    // Pendant la soirée : relire l'état toutes les 3 secondes (qui est arrivé, qui a envoyé)
    minuterie = setInterval(() => { if (s?.etat === 'ouverte' && !rejouer && !document.hidden) lire() }, 3000)
  })
  onDestroy(() => clearInterval(minuterie))

  const creer = (e) => { e.preventDefault(); essayer(async () => { await api.post('/api/soirees', { ...nouvelle, nom: titre }); titreEcrit = null; await lire() }) }
  const coller = () => essayer(async () => { await api.put(`/api/soirees/${s.id}/chansons`, { texte: collage }); collage = ''; await lire() })
  const attendus = () => new Set(s.participants.map((p) => p.prenom))
  async function basculer(invite) {
    const voulus = invites.filter((i) => i.actif && (attendus().has(i.prenom) !== (i.id === invite.id))).map((i) => i.id)
    await essayer(async () => { await api.put(`/api/soirees/${s.id}/attendus`, { invites: voulus }); await lire() })
  }
  async function ajouter(e) {
    e.preventDefault()
    await essayer(async () => {
      const { id } = await api.post('/api/invites', { prenom })
      const voulus = [...invites.filter((i) => attendus().has(i.prenom)).map((i) => i.id), id]
      await api.put(`/api/soirees/${s.id}/attendus`, { invites: voulus })
      prenom = ''
      await lire()
    })
  }
  const ouvrir = () => essayer(async () => { await api.post(`/api/soirees/${s.id}/ouvrir`); await lire() })
  const enCours = (id) => essayer(async () => { await api.post(`/api/soirees/${s.id}/chanson-en-cours`, { chanson_id: id }); await lire() })
  const liberer = (p) => essayer(async () => { await api.post(`/api/soirees/${s.id}/liberer`, { participation_id: p.id }); await lire() })
  const voirForcer = () => essayer(async () => { forcer = await api.get(`/api/soirees/${s.id}/forcer`) })
  const devoiler = (force) => essayer(async () => {
    await api.post(`/api/soirees/${s.id}/devoiler`, { forcer: force, mode })
    forcer = null
    rejouer = s.id
    await lire()
  })
  const archiver = () => essayer(async () => { await api.post(`/api/soirees/${s.id}/archiver`); await lire() })

  const libelle = { attendu: 'Pas arrivé', en_cours: 'Note', envoye: 'Envoyé', ecarte: 'Écarté' }
  let envoyes = $derived(s ? s.participants.filter((p) => p.etat === 'envoye').length : 0)
  let passees = $derived((soirees || []).filter((x) => x.etat === 'archivee'))
</script>

{#if rejouer}
  <Devoilement soiree={rejouer} onferme={() => { rejouer = null; lire() }} />
{:else if accueil && s}
  <Accueil soiree={s} onferme={() => (accueil = false)} />
{:else}
  <header class="mb-5">
    <h1 class="titre">{s ? s.nom : 'Soirée'}</h1>
    {#if s}<p class="mt-1 text-sm text-muted-foreground">{s.concours} {s.annee}, {EMISSIONS[s.emission].toLowerCase()}</p>{/if}
  </header>

  {#if erreur}<p class="mb-4 rounded-xl border border-destructive/60 px-4 py-2 text-sm" role="alert">{erreur}</p>{/if}

  {#if soirees === null}
    <p class="text-sm text-muted-foreground">Lecture…</p>

  {:else if !s}
    <form class="grid max-w-md gap-4 rounded-2xl border bg-card p-5" onsubmit={creer}>
      <h2 class="text-lg font-semibold">Nouvelle soirée</h2>
      <label class="champ">Concours
        <select bind:value={nouvelle.concours}>{#each concours as c}<option>{c}</option>{/each}</select>
        <span class="text-xs text-muted-foreground">Un autre concours ? Ajoute-le dans les Réglages.</span>
      </label>
      <div class="grid grid-cols-2 gap-3">
        <label class="champ">Année<input type="number" bind:value={nouvelle.annee} min="1956" max="2100" required /></label>
        <label class="champ">Émission
          <select bind:value={nouvelle.emission}>
            {#each Object.entries(EMISSIONS) as [cle, nom]}<option value={cle}>{nom}</option>{/each}
          </select>
        </label>
      </div>
      <label class="champ">Ville où le concours est organisé
        <input bind:value={nouvelle.ville} maxlength="60" placeholder="Burgas" />
      </label>
      <label class="champ">Titre de l'évènement
        <input value={titre} oninput={(e) => (titreEcrit = e.currentTarget.value)} required maxlength="80" />
        <span class="text-xs text-muted-foreground">
          {#if titreEcrit === null}Fabriqué d'après le concours, la ville, l'année et l'émission. Tu peux l'écrire autrement.
          {:else}<button type="button" class="underline" onclick={() => (titreEcrit = null)}>Revenir au titre fabriqué</button>{/if}
        </span>
      </label>
      <Button type="submit" size="lg">Créer la soirée</Button>
    </form>

  {:else if s.etat === 'brouillon'}
    <div class="grid gap-4 lg:grid-cols-2">
      <section class="rounded-2xl border bg-card p-5">
        <h2 class="text-lg font-semibold">Chansons <span class="font-normal text-muted-foreground">{s.chansons.length || ''}</span></h2>
        {#if s.chansons.length}
          <ol class="mt-3 grid gap-1 text-sm">
            {#each s.chansons as c (c.id)}
              <li class="flex gap-2"><span class="w-6 text-right text-muted-foreground">{c.ordre}</span>
                <span>{drapeau(c.pays, c.code_pays)} {c.pays}</span>
                <span class="truncate text-muted-foreground">{c.artiste}{c.titre ? ', ' + c.titre : ''}</span></li>
            {/each}
          </ol>
        {/if}
        <label class="champ mt-4">{s.chansons.length ? 'Remplacer la liste' : 'Coller la liste, dans l\'ordre de passage'}
          <textarea bind:value={collage} rows="5" placeholder={'Une chanson par ligne :\nFrance ; Artiste ; Titre\nSuède ; Artiste ; Titre'}></textarea>
        </label>
        <p class="mt-1 text-xs text-muted-foreground">Pays, artiste et titre séparés par un point-virgule ou une tabulation.</p>
        <Button class="mt-3" variant="outline" onclick={coller} disabled={!collage.trim()}>Enregistrer la liste</Button>
      </section>

      <section class="rounded-2xl border bg-card p-5">
        <h2 class="text-lg font-semibold">Invités attendus <span class="font-normal text-muted-foreground">{s.participants.length || ''}</span></h2>
        <ul class="mt-3 flex flex-wrap gap-2">
          {#each invites.filter((i) => i.actif) as i (i.id)}
            <li><button class="pastille" aria-pressed={attendus().has(i.prenom)} onclick={() => basculer(i)}>{i.prenom}</button></li>
          {/each}
        </ul>
        <form class="mt-4 flex gap-2" onsubmit={ajouter}>
          <input class="saisie flex-1" bind:value={prenom} placeholder="Prénom" maxlength="40" aria-label="Prénom d'un nouvel invité" required />
          <Button type="submit" variant="outline">Ajouter</Button>
        </form>
        <p class="mt-2 text-xs text-muted-foreground">Tu notes aussi : ajoute ton prénom.</p>
      </section>
    </div>

    <Images soiree={s} onchange={lire} />

    <section class="mt-4 flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-5">
      <div class="mr-auto">
        <h2 class="text-lg font-semibold">Prêt ?</h2>
        <p class="text-sm text-muted-foreground">Le lien des invités existe déjà : tu peux l'envoyer avant d'ouvrir. Une fois la soirée ouverte, la liste ne change plus.</p>
      </div>
      <Button variant="outline" onclick={() => (accueil = true)}>Écran d'accueil</Button>
      <Button size="lg" onclick={ouvrir} disabled={!s.chansons.length || !s.participants.length}>Ouvrir la soirée</Button>
    </section>

  {:else if s.etat === 'ouverte'}
    <section class="rounded-2xl border bg-card p-5">
      <div class="flex flex-wrap items-end gap-4">
        <p class="chiffre text-6xl" aria-label="{envoyes} classements envoyés sur {s.participants.length}">
          {envoyes}<span class="text-3xl text-muted-foreground">/{s.participants.length}</span>
        </p>
        <p class="mr-auto pb-1 text-sm text-muted-foreground">classements envoyés</p>
        <Button variant="outline" onclick={() => (accueil = true)}>Écran d'accueil</Button>
      </div>
      <ul class="mt-4 grid gap-2 sm:grid-cols-2">
        {#each s.participants as p (p.id)}
          <li class="flex items-center gap-3 rounded-xl border px-3 py-2">
            <span class="size-2.5 rounded-full {p.etat === 'envoye' ? 'bg-primary' : p.etat === 'en_cours' ? 'bg-foreground/50' : 'border border-muted-foreground'}"></span>
            <span class="font-medium">{p.prenom}</span>
            <span class="mr-auto text-sm text-muted-foreground">{libelle[p.etat]}{p.etat === 'en_cours' ? ` ${p.notees} / ${s.chansons.length}` : ''}</span>
            {#if p.pris}<button class="text-xs text-muted-foreground underline" onclick={() => liberer(p)} title="Téléphone changé ou mauvais prénom : les notes sont gardées">Libérer</button>{/if}
          </li>
        {/each}
      </ul>

      <div class="mt-5 flex flex-wrap items-center gap-3 border-t pt-4">
        <fieldset class="mr-auto flex gap-2 text-sm" aria-label="Dévoilement">
          <button class="pastille" aria-pressed={mode === 'court'} onclick={() => (mode = 'court')}>Court : 8, 10 et 12</button>
          <button class="pastille" aria-pressed={mode === 'complet'} onclick={() => (mode = 'complet')}>Complet</button>
        </fieldset>
        {#if s.tous_envoye}
          <Button size="lg" onclick={() => devoiler(false)}>Dévoiler</Button>
        {:else}
          <Button variant="outline" onclick={voirForcer}>Forcer le dévoilement</Button>
        {/if}
      </div>
      {#if forcer}
        <div class="mt-4 rounded-xl border border-primary/50 p-4 text-sm" role="alertdialog" aria-label="Forcer le dévoilement">
          <p class="font-medium">Tout le monde n'a pas envoyé.</p>
          {#each forcer.pris as f}<p class="mt-1">{f.prenom} : son classement du moment sera pris ({f.notees} chansons sur {s.chansons.length}).</p>{/each}
          {#if forcer.ecartes.length}<p class="mt-1">{forcer.ecartes.join(', ')} : rien de noté, ne comptera pas.</p>{/if}
          <p class="mt-1 text-muted-foreground">Ensuite, plus personne ne peut modifier ses notes.</p>
          <div class="mt-3 flex gap-2"><Button onclick={() => devoiler(true)}>Dévoiler quand même</Button><Button variant="outline" onclick={() => (forcer = null)}>Attendre</Button></div>
        </div>
      {/if}
    </section>

    <Images soiree={s} onchange={lire} />

    <section class="mt-4 rounded-2xl border bg-card p-5">
      <h2 class="text-lg font-semibold">Chanson en cours</h2>
      <p class="text-sm text-muted-foreground">Facultatif : touche la chanson qui passe, les téléphones la mettent en avant.</p>
      <ol class="mt-3 grid gap-1 sm:grid-cols-2">
        {#each s.chansons as c (c.id)}
          <li><button class="ligne" aria-pressed={s.chanson_en_cours === c.id} onclick={() => enCours(s.chanson_en_cours === c.id ? null : c.id)}>
            <span class="w-6 text-right text-muted-foreground">{c.ordre}</span><span>{drapeau(c.pays, c.code_pays)} {c.pays}</span>
          </button></li>
        {/each}
      </ol>
    </section>

  {:else if s.etat === 'devoilement'}
    <section class="rounded-2xl border bg-card p-5">
      <h2 class="text-lg font-semibold">Le dévoilement est en cours</h2>
      <p class="mt-1 text-sm text-muted-foreground">Les points sont figés. Tourne le téléphone en paysage et recopie l'écran sur la télé.</p>
      <Button class="mt-4" size="lg" onclick={() => (rejouer = s.id)}>Reprendre le dévoilement</Button>
    </section>

  {:else}
    <section class="flex flex-wrap items-center gap-3 rounded-2xl border bg-card p-5">
      <div class="mr-auto">
        <h2 class="text-lg font-semibold">Soirée dévoilée</h2>
        <p class="text-sm text-muted-foreground">Les invités voient les résultats sur leur téléphone. Archiver ferme leur lien et permet de préparer la soirée suivante.</p>
      </div>
      <Button variant="outline" onclick={() => (rejouer = s.id)}>Rejouer le dévoilement</Button>
      <Button onclick={archiver}>Archiver</Button>
    </section>
  {/if}

  {#if passees.length}
    <section class="mt-8">
      <h2 class="text-lg font-semibold">Soirées passées</h2>
      <ul class="mt-3 grid gap-2 sm:grid-cols-2">
        {#each passees as p (p.id)}
          <li class="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
            <span class="mr-auto"><span class="font-medium">{p.nom}</span><br /><span class="text-sm text-muted-foreground">{p.concours} {p.annee}, {EMISSIONS[p.emission].toLowerCase()}</span></span>
            <Button variant="outline" onclick={() => (rejouer = p.id)}>Rejouer</Button>
          </li>
        {/each}
      </ul>
    </section>
  {/if}
{/if}
