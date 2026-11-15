<script>
  // Première version : la liste des soirées, lue chez le serveur. Les écrans de préparation,
  // d'accueil, de notation et de dévoilement arrivent aux étapes suivantes du plan (docs/dossier.md § 6).
  import { onMount } from 'svelte'
  import { api } from '$lib/api.js'
  let { ondeconnecte } = $props()

  const etats = { brouillon: 'En préparation', ouverte: 'En cours', devoilement: 'Dévoilement', devoilee: 'Dévoilée', archivee: 'Archivée' }
  const emissions = { demi1: 'Première demi-finale', demi2: 'Seconde demi-finale', finale: 'Finale', unique: 'Soirée unique' }
  let soirees = $state(null)
  let erreur = $state('')

  onMount(async () => {
    try {
      soirees = await api.get('/api/soirees')
    } catch (e) {
      if (e.statut === 401) ondeconnecte()
      else erreur = e.message
    }
  })
</script>

<header class="mb-5">
  <p class="etiquette">Douze points</p>
  <h1 class="titre">Soirée</h1>
</header>

{#if erreur}
  <p class="text-sm text-destructive" role="alert">{erreur}</p>
{:else if soirees === null}
  <p class="text-sm text-muted-foreground">Lecture…</p>
{:else if soirees.length === 0}
  <p class="rounded-2xl border bg-card p-5 text-sm text-muted-foreground">
    Aucune soirée pour l'instant. Le serveur est prêt (notes, classements, points, dévoilement) ; l'écran pour préparer une soirée arrive à l'étape suivante.
  </p>
{:else}
  <ul class="grid gap-3 sm:grid-cols-2" aria-label="Soirées">
    {#each soirees as s (s.id)}
      <li class="rounded-2xl border bg-card p-5">
        <p class="etiquette">{s.concours} {s.annee} · {emissions[s.emission]}</p>
        <p class="mt-1 text-lg font-semibold">{s.nom}</p>
        <p class="mt-2 text-sm text-primary">{etats[s.etat]}</p>
      </li>
    {/each}
  </ul>
{/if}
