<script>
  // 1.6 : le dernier écran de la télé, après le podium : tous les duos de jumeaux de vote d'un coup (choix de Julien).
  // Relu toutes les 5 s : un duo s'allume (📸) dès qu'une photo de lui est arrivée. Les invités sans jumeau
  // n'apparaissent pas (personne n'est montré seul). Jamais de note ni de pourcentage : la tranche seule.
  import { onMount, onDestroy } from 'svelte'
  import { api } from '$lib/api.js'
  let { soiree, onferme } = $props()

  let j = $state(null)
  let erreur = $state('')
  async function lire() {
    try { j = await api.get(`/api/soirees/${soiree}/jumeaux`) } catch (e) { erreur = e.message }
  }
  let minuterie
  onMount(() => { lire(); minuterie = setInterval(() => { if (!document.hidden) lire() }, 5000) })
  onDestroy(() => clearInterval(minuterie))
  let immortalises = $derived(j ? j.duos.filter((d) => d.photos > 0).length : 0)
</script>

<div class="fixed inset-0 z-30 flex flex-col bg-background p-[max(1rem,env(safe-area-inset-top))]">
  <div class="flex items-start gap-3">
    <div class="mr-auto">
      <h1 class="font-light tracking-tight" style="font-size: clamp(1.4rem, 6vh, 2.8rem)">Les jumeaux de vote</h1>
      <p class="text-muted-foreground" style="font-size: clamp(0.85rem, 2.8vh, 1.2rem)">Ceux dont les notes se ressemblent le plus.</p>
    </div>
    <button class="commande" onclick={onferme}>Fermer</button>
  </div>

  {#if erreur}<p class="mt-6" role="alert">{erreur}</p>
  {:else if j && !j.duos.length}
    <p class="mt-10 text-center text-xl text-muted-foreground">Pas assez de chansons notées en commun pour former des duos.</p>
  {:else if j}
    <ul class="mosaique my-auto" aria-label="Duos de jumeaux de vote" style="--n: {Math.min(j.duos.length, 4)}">
      {#each j.duos as d, i (d.cle)}
        <li class="duo" class:allume={d.photos > 0} style="animation-delay: {i * 0.12}s">
          <span class="noms"><span>{d.invites[0].prenom}</span><span class="lien" aria-hidden="true">{d.reciproques ? '⇄' : '→'}</span><span>{d.invites[1].prenom}</span></span>
          <span class="tranche">{d.tranche}{d.reciproques ? ' · réciproques' : ''}</span>
          {#if d.photos > 0}<span class="photo">📸 immortalisés</span>{/if}
        </li>
      {/each}
    </ul>
    <p class="text-center text-muted-foreground" style="font-size: clamp(0.9rem, 3vh, 1.3rem)">
      {#if j.photos.actives}
        Prenez vos téléphones pour vous immortaliser{immortalises ? ` · ${immortalises} duo${immortalises > 1 ? 's' : ''} sur ${j.duos.length}` : ''}.
      {:else}Bravo aux jumeaux de la soirée !{/if}
    </p>
  {/if}
</div>

<style>
  .commande { min-height: 2.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--background); padding: 0 1rem; color: var(--muted-foreground); }
  .mosaique { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 1.2vw; width: 100%; padding: 2vh 0; }
  @media (orientation: portrait) { .mosaique { grid-template-columns: 1fr; } }
  .duo { display: flex; min-width: 0; flex-direction: column; align-items: center; gap: 0.4vh; border-radius: 1rem; border: 1px solid var(--border);
    background: var(--card); padding: 2.2vh 1vw; text-align: center; animation: entrer 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
    transition: box-shadow 0.8s, border-color 0.8s, background 0.8s; }
  .duo .noms { display: flex; max-width: 100%; align-items: baseline; justify-content: center; gap: 0.6vw; font-size: clamp(1rem, 5vh, 2.2rem); font-weight: 300; }
  .duo .noms span:not(.lien) { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .duo .lien { color: var(--primary); }
  .duo .tranche { font-size: clamp(0.75rem, 2.6vh, 1.1rem); color: var(--muted-foreground); }
  .duo .photo { font-size: clamp(0.75rem, 2.6vh, 1.1rem); color: var(--primary); }
  /* un duo immortalisé s'allume sous un projecteur */
  .duo.allume { border-color: color-mix(in oklab, var(--primary) 70%, var(--border));
    background: radial-gradient(120% 100% at 50% -30%, color-mix(in oklab, var(--primary) 30%, var(--card)), var(--card) 75%);
    box-shadow: 0 0 4vh color-mix(in oklab, var(--primary) 35%, transparent); }
  @keyframes entrer { from { opacity: 0; transform: translateY(3vh) scale(0.96); } to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .duo { animation: none; transition: none; } }
</style>
