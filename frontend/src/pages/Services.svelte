<script>
  // « Connexion » : une tuile par service extérieur, avec ce que Douze points y lit et y écrit.
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'

  let services = $state([])
  let erreur = $state('')
  let enCours = $state(false)

  async function lire(verifier) {
    erreur = ''
    enCours = verifier
    try { services = await api.get('/api/services' + (verifier ? '?verifier=true' : '')) } catch (e) { erreur = e.message }
    enCours = false
  }
  onMount(() => lire(false))
</script>

<header class="mb-5">
  <h1 class="titre">Connexion</h1>
</header>
{#if erreur}<p class="mb-3 text-sm text-destructive" role="alert">{erreur}</p>{/if}

<ul class="grid gap-3 sm:grid-cols-2" aria-label="Services">
  {#each services as s (s.id)}
    <li class="rounded-2xl border bg-card p-5">
      <p class="flex items-center gap-2 text-lg font-semibold">
        <span class="size-2.5 rounded-full {s.ok === true ? 'bg-primary' : s.ok === false ? 'bg-destructive' : s.regle ? 'bg-foreground/50' : 'border border-muted-foreground'}"></span>
        {s.nom}
        <span class="ml-auto text-sm font-normal text-muted-foreground">{!s.regle ? 'Pas relié' : s.ok === true ? 'Répond' : s.ok === false ? 'Ne répond pas' : 'Relié'}</span>
      </p>
      <dl class="mt-3 grid gap-2 text-sm">
        <div><dt class="text-muted-foreground">Ce qui est lu</dt><dd>{s.lit}</dd></div>
        <div><dt class="text-muted-foreground">Ce qui est écrit</dt><dd>{s.ecrit}</dd></div>
        {#if !s.regle}<div><dt class="text-muted-foreground">Pour le relier, dans la stack</dt><dd>{s.reglage}</dd></div>{/if}
      </dl>
      {#if s.detail}<p class="mt-3 text-sm" role="status">{s.detail}</p>{/if}
      {#if s.regle}<Button class="mt-4" variant="outline" onclick={() => lire(true)} disabled={enCours}>{enCours ? 'Vérification…' : 'Vérifier'}</Button>{/if}
    </li>
  {/each}
</ul>
