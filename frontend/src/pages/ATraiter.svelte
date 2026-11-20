<script>
  // 1.9 : « À traiter » (choix de Julien du 20/11/2026). Après le dévoilement, la soirée attend ses vrais votes :
  // points du jury et du public officiels, rang officiel (ex æquo départagés par le concours), et pour une
  // demi-finale les qualifiés. « Clôturer la soirée » l'envoie à carnet et fige le résultat officiel (le journal lu
  // par Gazette pour « Good Evening Europe! »). Clôturer avec ce qui est saisi est permis ; ce qui manque est affiché,
  // et une nouvelle clôture complète plus tard (vrais votes d'une demi connus après la finale).
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { EMISSIONS, normaliser } from '$lib/pays.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Drapeau from '$lib/Drapeau.svelte'
  let { onnombre = () => {} } = $props()

  let liste = $state(null)
  let ouverte = $state(null)       // la soirée en cours de saisie : { s, chansons, saisie }
  let erreur = $state('')
  let message = $state('')
  let occupe = $state(false)
  let dateFinale = $state('')

  async function lire() {
    try {
      liste = await api.get('/api/a-traiter')
      onnombre(liste.nombre)
    } catch (e) { erreur = e.message }
  }
  onMount(lire)

  async function ouvrir(s) {
    erreur = ''; message = ''
    const d = await api.get(`/api/soirees/${s.id}`)
    const chansons = d.chansons.map(normaliser)
    ouverte = {
      s, chansons,
      saisie: Object.fromEntries(chansons.map((c) => [c.id, {
        jury: c.officiel_jury ?? '', public: c.officiel_public ?? '', rang: c.officiel_rang ?? '',
        qualifie: c.officiel_qualifie === null || c.officiel_qualifie === undefined ? null : !!c.officiel_qualifie,
      }])),
    }
    dateFinale = ''
  }
  const corps = () => ({ resultats: Object.entries(ouverte.saisie).map(([id, v]) => ouverte.s.demi
    ? { chanson_id: +id, qualifie: !!v.qualifie }
    : { chanson_id: +id, jury: v.jury, public: v.public, rang: v.rang }) })
  async function enregistrer() {
    erreur = ''; message = ''; occupe = true
    try {
      await api.put(`/api/soirees/${ouverte.s.id}/officiel`, corps())
      message = 'Vrais votes enregistrés.'
      await lire()
      ouverte.s = liste.soirees.find((x) => x.id === ouverte.s.id) ?? ouverte.s
    } catch (e) { erreur = e.message } finally { occupe = false }
  }
  async function cloturer() {
    erreur = ''; message = ''; occupe = true
    try {
      await api.put(`/api/soirees/${ouverte.s.id}/officiel`, corps())
      const r = await api.post(`/api/soirees/${ouverte.s.id}/cloturer`, ouverte.s.demi && dateFinale ? { date_finale: dateFinale } : {})
      message = `Soirée clôturée (résultat officiel n° ${r.version}) · ${r.carnet || 'carnet : rien à envoyer'}.`
      ouverte = null
      await lire()
    } catch (e) { erreur = e.message } finally { occupe = false }
  }
  let aCloturer = $derived(liste ? liste.soirees.filter((s) => s.a_cloturer) : [])
  let cloturees = $derived(liste ? liste.soirees.filter((s) => !s.a_cloturer) : [])
  let qualifies = $derived(ouverte?.s.demi ? Object.values(ouverte.saisie).filter((v) => v.qualifie).length : 0)
</script>

<h1 class="mb-1 text-2xl font-light tracking-tight">À traiter</h1>
<p class="mb-4 text-sm text-muted-foreground">Après le dévoilement : les vrais votes du concours, puis la clôture, qui envoie la soirée à carnet et prépare le magazine de Gazette.</p>
{#if erreur}<p class="mb-3 text-sm text-destructive" role="alert">{erreur}</p>{/if}
{#if message}<p class="mb-3 text-sm text-primary" role="status">{message}</p>{/if}

{#if ouverte}
  <section class="rounded-2xl border bg-card p-5" aria-label="Vrais votes de {ouverte.s.nom}">
    <div class="flex flex-wrap items-start gap-3">
      <div class="mr-auto min-w-0">
        <h2 class="text-lg font-semibold">{ouverte.s.nom}</h2>
        <p class="text-sm text-muted-foreground">{ouverte.s.demi
          ? 'Demi-finale : le soir même, l\'Europe ne publie que les qualifiés. Coche-les ; les points arriveront après la finale (nouvelle clôture).'
          : 'Les points du vrai jury et du vrai public. Le rang officiel ne sert qu\'en cas d\'ex æquo départagé par le concours.'}</p>
      </div>
      <Button variant="outline" onclick={() => (ouverte = null)}>Retour</Button>
    </div>

    {#if ouverte.s.demi}
      <p class="mt-3 text-sm" role="status">{qualifies} qualifié{qualifies > 1 ? 's' : ''} coché{qualifies > 1 ? 's' : ''} (en général 10).</p>
      <ul class="mt-2 grid gap-1 sm:grid-cols-2" aria-label="Qualifiés">
        {#each ouverte.chansons as c (c.id)}
          <li>
            <label class="ligne-q">
              <input type="checkbox" checked={!!ouverte.saisie[c.id].qualifie} onchange={(e) => (ouverte.saisie[c.id].qualifie = e.currentTarget.checked)} />
              <span class="truncate">{c.ordre}. <Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</span>
            </label>
          </li>
        {/each}
      </ul>
      <label class="mt-4 block text-sm">Date de la finale (pour « Rendez-vous samedi » dans le magazine, facultatif)
        <input type="date" class="mt-1 block rounded-lg border bg-background px-3 py-2" bind:value={dateFinale} />
      </label>
    {:else}
      <div class="mt-3 grid gap-1" role="table" aria-label="Vrais votes">
        <div class="vrai text-xs text-muted-foreground" role="row"><span></span><span>Jury</span><span>Public</span><span>Rang</span></div>
        {#each ouverte.chansons as c (c.id)}
          <div class="vrai" role="row">
            <span class="truncate">{c.ordre}. <Drapeau pays={c.pays} code={c.code_pays} />{c.pays}</span>
            <input class="saisie" type="number" min="0" inputmode="numeric" bind:value={ouverte.saisie[c.id].jury} aria-label="{c.pays} : vrais points du jury" />
            <input class="saisie" type="number" min="0" inputmode="numeric" bind:value={ouverte.saisie[c.id].public} aria-label="{c.pays} : vrais points du public" />
            <input class="saisie" type="number" min="1" inputmode="numeric" bind:value={ouverte.saisie[c.id].rang} aria-label="{c.pays} : rang officiel (si ex æquo)" />
          </div>
        {/each}
      </div>
    {/if}

    {#if ouverte.s.manques?.length}<p class="mt-3 text-sm text-muted-foreground">Encore à saisir : {ouverte.s.manques.join(' ; ')}. Tu peux clôturer quand même et compléter plus tard.</p>{/if}
    <div class="mt-4 flex flex-wrap gap-2">
      <Button variant="outline" onclick={enregistrer} disabled={occupe}>Enregistrer</Button>
      <Button onclick={cloturer} disabled={occupe}>{ouverte.s.a_cloturer ? 'Clôturer la soirée' : 'Clôturer à nouveau'}</Button>
    </div>
    <p class="mt-2 text-xs text-muted-foreground">La clôture envoie la soirée à carnet et fige le résultat officiel lu par Gazette. Une nouvelle clôture remplace la soirée dans carnet et fait une nouvelle version du résultat.</p>
  </section>
{:else if liste}
  {#if !liste.soirees.length}
    <p class="rounded-2xl border bg-card p-5 text-sm text-muted-foreground">Rien à traiter : aucune soirée dévoilée pour l'instant.</p>
  {/if}
  {#if aCloturer.length}
    <h2 class="mb-2 text-sm font-medium text-muted-foreground">À clôturer</h2>
    <ul class="mb-6 grid gap-2 sm:grid-cols-2">
      {#each aCloturer as s (s.id)}
        <li><button class="tuile a-faire" onclick={() => ouvrir(s)}>
          <span class="block font-medium">{s.nom}</span>
          <span class="block text-sm text-muted-foreground">{s.concours} {s.annee}, {EMISSIONS[s.emission].toLowerCase()}</span>
          <span class="mt-1 block text-sm">{s.manques.length ? s.manques.join(' ; ') : 'Vrais votes saisis : prête à clôturer'}</span>
        </button></li>
      {/each}
    </ul>
  {/if}
  {#if cloturees.length}
    <h2 class="mb-2 text-sm font-medium text-muted-foreground">Clôturées</h2>
    <ul class="grid gap-2 sm:grid-cols-2">
      {#each cloturees as s (s.id)}
        <li><button class="tuile" onclick={() => ouvrir(s)}>
          <span class="block font-medium">{s.nom}</span>
          <span class="block text-sm text-muted-foreground">Clôturée le {s.cloturee_le?.slice(0, 10)}{s.version ? ` · résultat n° ${s.version}` : ' · sans résultat officiel (avant la 1.9)'}</span>
          {#if s.manques.length}<span class="mt-1 block text-sm">À compléter : {s.manques.join(' ; ')}</span>{/if}
        </button></li>
      {/each}
    </ul>
  {/if}
{:else}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{/if}

<style>
  .tuile { display: block; width: 100%; min-height: 4.5rem; border-radius: 1rem; border: 1px solid var(--border); background: var(--card); padding: 0.9rem 1rem; text-align: left; }
  .tuile.a-faire { border-color: color-mix(in oklab, var(--primary) 60%, var(--border)); }
  .tuile:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
  .vrai { display: grid; grid-template-columns: minmax(0, 1fr) 4.5rem 4.5rem 3.5rem; gap: 0.4rem; align-items: center; }
  .saisie { min-height: 2.75rem; width: 100%; border-radius: 0.6rem; border: 1px solid var(--border); background: var(--background); padding: 0 0.5rem; text-align: right; }
  .ligne-q { display: flex; min-height: 2.75rem; align-items: center; gap: 0.6rem; border-radius: 0.6rem; border: 1px solid var(--border); padding: 0 0.75rem; }
  .ligne-q input { width: 1.2rem; height: 1.2rem; accent-color: var(--primary); }
</style>
