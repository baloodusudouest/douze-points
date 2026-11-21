<script>
  // Les vrais votes du concours, face à notre soirée. Tout le monde les voit dès qu'ils sont saisis ;
  // l'hôte connecté les saisit ici, depuis son téléphone, pendant que le concours donne ses résultats.
  import { drapeau } from '$lib/pays.js'
  let { resultats, parId, soiree = null, onchange } = $props()

  let saisie = $state(false)
  let valeurs = $state({})
  let erreur = $state('')
  let occupe = $state(false)

  let connus = $derived(resultats.vrais.filter((v) => v.total !== null))
  let tries = $derived([...connus].sort((a, b) => a.rang - b.rang))
  let comp = $derived(resultats.comparaison?.ensemble)

  function ouvrir() {
    valeurs = Object.fromEntries(resultats.vrais.map((v) => [v.chanson, { jury: v.jury ?? '', public: v.public ?? '' }]))
    saisie = true
  }
  async function enregistrer() {
    occupe = true; erreur = ''
    try {
      const r = await fetch(`/api/soirees/${soiree.id}/officiel`, { method: 'PUT', credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resultats: Object.entries(valeurs).map(([id, v]) => ({ chanson_id: +id, jury: v.jury, public: v.public })) }) })
      const x = await r.json().catch(() => ({}))
      if (!r.ok) throw new Error(x.detail || `Le serveur a répondu ${r.status}.`)
      saisie = false
      await onchange()
    } catch (x) { erreur = x.message } finally { occupe = false }
  }
</script>

{#if connus.length || soiree}
  <section class="mt-6 rounded-2xl border bg-card p-4" aria-label="Les vrais votes">
    <h2 class="text-lg font-semibold">Les vrais votes</h2>
    {#if comp}
      <p class="mt-1 text-sm text-muted-foreground">
        {comp.meme_gagnant ? 'Même gagnant que le concours !' : 'Pas le même gagnant que le concours.'}
        {comp.trois_premieres} chanson{comp.trois_premieres > 1 ? 's' : ''} en commun dans les trois premières ; écart moyen de {comp.ecart_moyen} place{comp.ecart_moyen > 1 ? 's' : ''}.
      </p>
    {/if}
    {#if tries.length}
      <ol class="mt-3 grid gap-1 text-sm">
        <li class="flex gap-2 px-2 text-xs text-muted-foreground"><span class="w-6 text-right">Vrai</span><span class="flex-1">Pays</span><span class="w-12 text-right">Points</span><span class="w-12 text-right">Chez nous</span></li>
        {#each tries as v (v.chanson)}
          {@const c = parId[v.chanson]}
          <li class="flex items-center gap-2 rounded-lg px-2 py-1 {v.rang === 1 ? 'bg-primary/20' : ''}">
            <span class="w-6 text-right text-muted-foreground">{v.rang}</span>
            <span class="min-w-0 flex-1 truncate">{drapeau(c.pays, c.code_pays)} {c.pays}</span>
            <span class="chiffre w-12 text-right text-base">{v.total}</span>
            <!-- 1.12 : notre pays n'a pas de rang chez nous (aucun point) -->
            <span class="w-12 text-right text-muted-foreground">{v.notre_rang == null ? '—' : `${v.notre_rang}e`}</span>
          </li>
        {/each}
      </ol>
    {:else}<p class="mt-1 text-sm text-muted-foreground">Pas encore saisis.</p>{/if}

    {#if soiree && !saisie}
      <button class="mt-3 w-full rounded-xl border py-2.5 text-sm" onclick={ouvrir}>{connus.length ? 'Modifier les vrais votes' : 'Saisir les vrais votes'}</button>
    {/if}
    {#if saisie}
      <div class="mt-3 grid gap-1">
        <p class="flex gap-2 px-1 text-xs text-muted-foreground"><span class="flex-1">Pays</span><span class="w-16 text-center">Jury</span><span class="w-16 text-center">Public</span></p>
        {#each resultats.vrais as v (v.chanson)}
          {@const c = parId[v.chanson]}
          <label class="flex items-center gap-2 text-sm">
            <span class="min-w-0 flex-1 truncate">{drapeau(c.pays, c.code_pays)} {c.pays}</span>
            <input class="saisie w-16 text-center" inputmode="numeric" aria-label="{c.pays} : vrais points du jury" bind:value={valeurs[v.chanson].jury} />
            <input class="saisie w-16 text-center" inputmode="numeric" aria-label="{c.pays} : vrais points du public" bind:value={valeurs[v.chanson].public} />
          </label>
        {/each}
        {#if erreur}<p class="text-sm text-destructive" role="alert">{erreur}</p>{/if}
        <div class="mt-2 grid grid-cols-2 gap-2">
          <button class="rounded-xl border py-2.5 text-sm" onclick={() => (saisie = false)}>Annuler</button>
          <button class="rounded-xl bg-primary py-2.5 text-sm text-primary-foreground" onclick={enregistrer} disabled={occupe}>Enregistrer les vrais votes</button>
        </div>
      </div>
    {/if}
  </section>
{/if}
