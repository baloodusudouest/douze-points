<script>
  // Les chansons dont le pays n'est pas reconnu : pas de drapeau. L'hôte choisit le pays dans la liste ;
  // « Retenir ce nom » relie le nom inconnu à ce pays pour les prochaines listes collées.
  import { api } from '$lib/api.js'
  import { drapeau, PAYS } from '$lib/pays.js'
  let { chansons, onchange } = $props()

  let sans = $derived(chansons.filter((c) => !drapeau(c.pays, c.code_pays)))
  let retenir = $state(true)
  let erreur = $state('')

  async function choisir(c, code) {
    if (!code) return
    erreur = ''
    try {
      await api.put(`/api/chansons/${c.id}/pays`, { code, nom: c.pays, retenir })
      await onchange()
    } catch (e) { erreur = e.message }
  }
</script>

{#if sans.length}
  <section class="mt-4 rounded-2xl border border-primary/60 bg-card p-5" role="alert" aria-label="Pays sans drapeau">
    <h2 class="text-lg font-semibold">{sans.length === 1 ? 'Un pays n\'est pas reconnu' : `${sans.length} pays ne sont pas reconnus`}</h2>
    <p class="mt-1 text-sm text-muted-foreground">Ils n'auront pas de drapeau. Choisis le pays qui correspond.</p>
    {#if erreur}<p class="mt-2 text-sm text-destructive">{erreur}</p>{/if}
    <ul class="mt-3 grid gap-2">
      {#each sans as c (c.id)}
        <li class="flex flex-wrap items-center gap-2">
          <span class="min-w-0 flex-1 truncate"><span class="text-muted-foreground">{c.ordre}.</span> {c.pays}</span>
          <select class="saisie w-56" aria-label="Pays de « {c.pays} »" onchange={(e) => choisir(c, e.currentTarget.value)}>
            <option value="">Choisir le pays…</option>
            {#each PAYS as p (p.code)}<option value={p.code}>{drapeau('', p.code)} {p.nom}</option>{/each}
          </select>
        </li>
      {/each}
    </ul>
    <label class="mt-3 flex items-center gap-2 text-sm"><input type="checkbox" bind:checked={retenir} class="size-4 accent-[var(--primary)]" />
      Retenir ces noms pour les prochaines listes</label>
  </section>
{/if}
