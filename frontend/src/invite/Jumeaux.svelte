<script>
  // 1.6 : sur le téléphone d'un invité, après le dévoilement, ses duos de jumeaux de vote : son jumeau, et ceux qui
  // l'ont choisi comme jumeau (un jumeau n'est pas toujours réciproque). Un bouton « Immortaliser » ouvre l'appareil
  // photo en selfie ; dès qu'une photo du duo est arrivée (de l'un ou de l'autre), le duo est « immortalisé ».
  // Jamais de note ni de pourcentage : une tranche (« Très proches »), qui ne laisse pas deviner les notes de l'autre.
  // 1.6.2 : le jumeau s'affiche toujours ; « Immortaliser » seulement si les photos sont actives (Immich réglé).
  import Photo from './Photo.svelte'
  let { jeton, tel, moi, jumeaux, photos = true, onenvoye = () => {} } = $props()

  const autre = (d) => d.invites.find((x) => x.id !== moi)
  const titre = (d) => d.reciproques ? `Ton jumeau de vote : ${autre(d).prenom}`
    : d.invites[0].id === moi ? `Ton jumeau de vote : ${autre(d).prenom}` : `Tu es le jumeau de vote de ${autre(d).prenom}`
</script>

{#if jumeaux.miens.length}
  <section class="mb-6 grid gap-3" aria-label="Jumeaux de vote">
    {#each jumeaux.miens as d (d.cle)}
      <div class="duo rounded-2xl border p-4" class:immortalise={d.photos > 0}>
        <p class="text-xs tracking-wide text-muted-foreground uppercase">{d.reciproques ? 'Jumeaux réciproques' : 'Jumeaux de vote'} · {d.tranche}</p>
        <p class="mt-1 text-xl font-light">{titre(d)}</p>
        <p class="mt-1 text-sm text-muted-foreground">Vos notes se ressemblent plus qu'avec n'importe qui d'autre ce soir.</p>
        {#if !photos}
        {:else if d.photos > 0}
          <p class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2 text-primary">📸 Immortalisés
            <Photo {jeton} {tel} duo={autre(d).id} selfie libelle="En reprendre une" classe="text-sm text-muted-foreground underline" {onenvoye} />
          </p>
        {:else}
          <Photo {jeton} {tel} duo={autre(d).id} selfie libelle={`Immortaliser avec ${autre(d).prenom}`} classe="immortaliser mt-3" {onenvoye} />
        {/if}
      </div>
    {/each}
    <!-- 1.8 : le selfie d'un duo s'affiche sur la télé (choix de Julien) : on le dit avant la photo -->
    {#if photos}<p class="text-xs text-muted-foreground">Votre selfie s'affiche sur la télé, puis part dans l'album de la soirée, chez l'hôte. Personne d'autre ne le voit sur son téléphone.</p>{/if}
  </section>
{:else if !jumeaux.a_jumeau}
  <p class="mb-6 rounded-2xl border bg-card p-4 text-sm text-muted-foreground">Pas de jumeau de vote ce soir : trop peu de chansons notées en commun avec les autres.</p>
{/if}

<style>
  .duo { background: radial-gradient(120% 90% at 50% -20%, color-mix(in oklab, var(--primary) 16%, var(--card)), var(--card) 70%); }
  .duo.immortalise { border-color: color-mix(in oklab, var(--primary) 60%, var(--border)); }
  :global(.immortaliser) { display: block; width: 100%; min-height: 3rem; border-radius: 0.8rem; background: var(--primary);
    color: var(--primary-foreground); font-size: 1rem; font-weight: 500; }
  :global(.immortaliser:disabled) { opacity: 0.7; }
</style>
