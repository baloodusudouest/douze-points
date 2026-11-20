<script>
  // 1.6 : le dernier écran de la télé, après le podium : tous les duos de jumeaux de vote d'un coup (choix de Julien).
  // Relu toutes les 3 s : un duo s'allume dès qu'une photo de lui est arrivée. Les invités sans jumeau
  // n'apparaissent pas (personne n'est montré seul). Jamais de note ni de pourcentage : la tranche seule.
  // 1.8 (choix de Julien du 20/11/2026) : le selfie d'un duo s'affiche. Arrivé pendant que cet écran est ouvert, il
  // passe d'abord en grand 6 s (polaroïd), puis se range dans la carte du duo ; un à la fois, les suivants attendent
  // leur tour. Ceux déjà là à l'ouverture vont directement dans leur carte. Image illisible : « 📸 immortalisés ».
  // La télé montre la vignette d'écran (JPEG réduit fait à la réception), jamais l'original.
  import { onMount, onDestroy } from 'svelte'
  import { prefersReducedMotion } from 'svelte/motion'
  import Camera from '@lucide/svelte/icons/camera'
  import { api } from '$lib/api.js'
  // 1.9 : le temps du selfie en grand se règle (Réglages › Dévoilement, « Selfie d'un duo en grand »)
  let { soiree, onferme, dureeSelfie = 6 } = $props()

  const EN_GRAND = $derived(dureeSelfie * 1000)
  let j = $state(null)
  let erreur = $state('')
  let vues = null                  // photos déjà connues (null : pas encore lu)
  let file = $state([])            // duos dont le selfie attend son passage en grand
  let enGrand = $state(null)       // le duo montré en grand
  let rangees = $state(new Set())  // duos dont la photo est dans la carte
  let illisibles = $state(new Set())
  let minuteGrand

  const adresse = (d) => `/api/soirees/${soiree}/photos/${d.photo}`

  async function lire() {
    try {
      j = await api.get(`/api/soirees/${soiree}/jumeaux`)
      const avec = j.duos.filter((d) => d.photo)
      if (vues === null) {                                   // à l'ouverture : tout va dans les cartes
        vues = new Map(avec.map((d) => [d.cle, d.photo]))
        rangees = new Set(avec.map((d) => d.cle))
        return
      }
      for (const d of avec) {
        if (vues.get(d.cle) === d.photo) continue
        vues.set(d.cle, d.photo)
        if (prefersReducedMotion.current) rangees = new Set([...rangees, d.cle])
        else if (!file.some((x) => x.cle === d.cle) && enGrand?.cle !== d.cle) file = [...file, d]
      }
      suivant()
    } catch (e) { erreur = e.message }
  }
  function suivant() {
    if (enGrand || !file.length) return
    enGrand = file[0]
    file = file.slice(1)
    minuteGrand = setTimeout(() => {
      rangees = new Set([...rangees, enGrand.cle])
      enGrand = null
      suivant()
    }, EN_GRAND)
  }
  function illisible(cle) { illisibles = new Set([...illisibles, cle]) }
  let minuterie
  onMount(() => { lire(); minuterie = setInterval(() => { if (!document.hidden) lire() }, 3000) })
  onDestroy(() => { clearInterval(minuterie); clearTimeout(minuteGrand) })
  let immortalises = $derived(j ? j.duos.filter((d) => d.photos > 0).length : 0)
  const noms = (d) => `${d.invites[0].prenom} et ${d.invites[1].prenom}`
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
        {@const montree = d.photo && rangees.has(d.cle) && !illisibles.has(d.cle)}
        <li class="duo" class:allume={d.photos > 0} style="animation-delay: {i * 0.12}s">
          {#if montree}
            <img class="photo-duo" src={adresse(d)} alt="Selfie de {noms(d)}" onerror={() => illisible(d.cle)} />
          {/if}
          <!-- 1.6.1 : les deux prénoms l'un sous l'autre, jamais coupés (deux « Grégoire … » se distinguent par la fin) -->
          <span class="noms" aria-label="{d.invites[0].prenom} {d.reciproques ? 'et' : 'a pour jumeau'} {d.invites[1].prenom}">
            <span class="nom">{d.invites[0].prenom}</span><span class="lien" aria-hidden="true">{d.reciproques ? '⇅' : '↓'}</span><span class="nom">{d.invites[1].prenom}</span>
          </span>
          <span class="tranche">{d.tranche}{d.reciproques ? ' · réciproques' : ''}</span>
          {#if d.photos > 0 && !montree}<span class="photo">📸 immortalisés</span>{/if}
        </li>
      {/each}
    </ul>
    <p class="text-center text-muted-foreground" style="font-size: clamp(0.9rem, 3vh, 1.3rem)">
      {#if j.photos.actives}
        Prenez vos téléphones pour vous immortaliser{immortalises ? ` · ${immortalises} duo${immortalises > 1 ? 's' : ''} sur ${j.duos.length}` : ''}.
      {:else}Bravo aux jumeaux de la soirée !{/if}
    </p>
  {/if}

  {#if enGrand}
    {#key enGrand.cle}
      <div class="voile" role="status" aria-live="polite">
        <figure class="polaroid">
          {#if illisibles.has(enGrand.cle)}
            <div class="sans-image"><Camera class="size-12" /></div>
          {:else}
            <img src={adresse(enGrand)} alt="Selfie de {noms(enGrand)}" onerror={() => illisible(enGrand.cle)} />
          {/if}
          <figcaption>{noms(enGrand)}</figcaption>
        </figure>
        <p class="legende">Immortalisés · {enGrand.tranche}</p>
        <div class="eclair" aria-hidden="true"></div>
      </div>
    {/key}
  {/if}
</div>

<style>
  .commande { min-height: 2.75rem; border-radius: 999px; border: 1px solid var(--border); background: var(--background); padding: 0 1rem; color: var(--muted-foreground); }
  .mosaique { display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr)); gap: 1.2vw; width: 100%; padding: 2vh 0; }
  @media (orientation: portrait) { .mosaique { grid-template-columns: 1fr; } }
  .duo { display: flex; min-width: 0; flex-direction: column; align-items: center; gap: 0.8vh; border-radius: 1rem; border: 1px solid var(--border);
    background: var(--card); padding: 2.2vh 1vw; text-align: center; animation: entrer 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
    transition: box-shadow 0.8s, border-color 0.8s, background 0.8s; }
  .photo-duo { width: 100%; max-height: 34vh; object-fit: cover; aspect-ratio: 4 / 3; border-radius: 0.6rem; animation: poser 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .duo .noms { display: flex; max-width: 100%; flex-direction: column; align-items: center; line-height: 1.15;
    font-size: clamp(1rem, 4.6vh, 2.1rem); font-weight: 300; }
  /* le prénom entier, sur deux lignes s'il le faut, jamais « … » */
  .duo .nom { max-width: 100%; overflow-wrap: anywhere; text-wrap: balance; }
  .duo .lien { color: var(--primary); font-size: 0.7em; line-height: 1; margin: 0.15em 0; }
  .duo .tranche { font-size: clamp(0.75rem, 2.6vh, 1.1rem); color: var(--muted-foreground); }
  .duo .photo { font-size: clamp(0.75rem, 2.6vh, 1.1rem); color: var(--primary); }
  /* un duo immortalisé s'allume sous un projecteur */
  .duo.allume { border-color: color-mix(in oklab, var(--primary) 70%, var(--border));
    background: radial-gradient(120% 100% at 50% -30%, color-mix(in oklab, var(--primary) 30%, var(--card)), var(--card) 75%);
    box-shadow: 0 0 4vh color-mix(in oklab, var(--primary) 35%, transparent); }
  .voile { position: absolute; inset: 0; z-index: 5; display: grid; place-content: center; justify-items: center; background: rgba(12, 10, 9, 0.85); }
  .polaroid { margin: 0; padding: 1.4vh 1.4vh 2vh; border-radius: 0.4rem; background: #f6f0ff; box-shadow: 0 3vh 8vh rgba(0, 0, 0, 0.6);
    animation: grand 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
  .polaroid img, .sans-image { display: block; width: min(70vw, 100vh); height: min(52vw, 70vh); object-fit: cover; border-radius: 2px; }
  .sans-image { display: grid; place-items: center; background: #2a2530; color: #c9bfb2; }
  .polaroid figcaption { margin-top: 1.2vh; text-align: center; color: #1b1035; font-size: clamp(1.1rem, 4vh, 1.9rem); font-weight: 600; }
  .legende { margin-top: 2.4vh; color: var(--primary); font-size: clamp(1rem, 3.2vh, 1.5rem); }
  .eclair { pointer-events: none; position: absolute; inset: 0; background: #fff; animation: eclair 0.7s ease-out both; }
  @keyframes entrer { from { opacity: 0; transform: translateY(3vh) scale(0.96); } to { opacity: 1; transform: none; } }
  @keyframes poser { from { opacity: 0; transform: scale(0.6); } to { opacity: 1; transform: none; } }
  @keyframes grand { 0% { opacity: 0; transform: scale(0.4) rotate(-4deg); } 60% { opacity: 1; transform: scale(1.03) rotate(1deg); } 100% { opacity: 1; transform: rotate(-1deg); } }
  @keyframes eclair { from { opacity: 0.9; } to { opacity: 0; } }
  @media (prefers-reduced-motion: reduce) { .duo, .photo-duo, .polaroid { animation: none; transition: none; } .eclair { display: none; } }
</style>
