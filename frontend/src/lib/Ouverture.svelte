<script>
  // L'ouverture : dans le noir, trois projecteurs viennent se poser sur le « 12 », qui se met à briller,
  // puis sa lumière gagne tout l'écran et laisse voir la page. Jouée une fois par session, 2,6 secondes ;
  // un toucher la passe. Si l'appareil demande moins d'animations, elle n'est pas jouée du tout.
  import { onMount } from 'svelte'

  // `toujours` : jouée à chaque fois (le démarrage d'une soirée), et non une fois par session.
  // `onfin` : appelé quand elle s'efface, qu'elle ait été jouée, passée d'un toucher ou sautée.
  let { toujours = false, onfin = () => {} } = $props()

  const CLE = 'douze-points:ouverture'
  let visible = $state(false)
  let fin

  function finir() {
    clearTimeout(fin)
    visible = false
    onfin()
  }

  onMount(() => {
    let deja = false
    if (!toujours) {
      try { deja = sessionStorage.getItem(CLE) === '1'; sessionStorage.setItem(CLE, '1') } catch { /* stockage fermé : on la joue */ }
    }
    if (deja || matchMedia('(prefers-reduced-motion: reduce)').matches) { onfin(); return }
    visible = true
    fin = setTimeout(finir, 2600)
    return () => clearTimeout(fin)
  })
</script>

{#if visible}
  <button class="ouverture" aria-label="Passer l'ouverture" onclick={finir}>
    <span class="halo"></span>
    <svg viewBox="0 0 400 400" aria-hidden="true">
      <defs>
        <linearGradient id="o-faisceau" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#e5559f" stop-opacity="0.75" /><stop offset="1" stop-color="#e5559f" stop-opacity="0" />
        </linearGradient>
      </defs>
      <!-- trois projecteurs accrochés en haut ; chacun pivote autour de sa lampe pour venir sur le 12 -->
      <g class="faisceau gauche"><path d="M52 -20h16l70 330H-18z" fill="url(#o-faisceau)" transform="rotate(-24 60 -20)" /></g>
      <g class="faisceau centre"><path d="M192 -20h16l62 330H130z" fill="url(#o-faisceau)" /></g>
      <g class="faisceau droite"><path d="M332 -20h16l70 330H262z" fill="url(#o-faisceau)" transform="rotate(24 340 -20)" /></g>
      <g class="douze" fill="none" stroke-width="13" stroke-linecap="round" stroke-linejoin="round">
        <path d="M128 196l34-25v136" />
        <path d="M206 205c0-21.500 16-36 36.500-36s36.500 14.500 36.500 35c0 17-10 28.500-28.500 45.500L206 305h75" />
      </g>
    </svg>
  </button>
{/if}

<style>
  .ouverture {
    position: fixed; inset: 0; z-index: 60; display: grid; place-items: center; overflow: hidden;
    background: #0b0a09; cursor: default;
    animation: lever 2.6s cubic-bezier(0.4, 0, 0.2, 1) forwards;
  }
  svg { position: relative; width: min(78vw, 78vh); height: auto; overflow: visible; }

  .faisceau { opacity: 0; transform-box: view-box; }
  .gauche { transform-origin: 60px -20px; animation: balayer-gauche 1.25s cubic-bezier(0.2, 0.7, 0.2, 1) 0.1s forwards; }
  .centre { transform-origin: 200px -20px; animation: allumer 0.9s ease-out 0.45s forwards; }
  .droite { transform-origin: 340px -20px; animation: balayer-droite 1.25s cubic-bezier(0.2, 0.7, 0.2, 1) 0.25s forwards; }

  .douze { stroke: #3a3531; animation: briller 2.6s ease-out forwards; }

  /* la lumière du 12 : un halo qui grandit depuis le centre jusqu'à couvrir l'écran */
  .halo {
    position: absolute; left: 50%; top: 55%; width: 40vmax; height: 40vmax; border-radius: 50%;
    background: radial-gradient(circle, rgb(242 236 226 / 0.55) 0%, rgb(229 85 159 / 0.35) 35%, rgb(229 85 159 / 0) 70%);
    transform: translate(-50%, -50%) scale(0); opacity: 0;
    animation: illuminer 2.6s ease-in forwards;
  }

  @keyframes balayer-gauche { 0% { opacity: 0; transform: rotate(-38deg); } 30% { opacity: 1; } 100% { opacity: 1; transform: rotate(0deg); } }
  @keyframes balayer-droite { 0% { opacity: 0; transform: rotate(38deg); } 30% { opacity: 1; } 100% { opacity: 1; transform: rotate(0deg); } }
  @keyframes allumer { from { opacity: 0; } to { opacity: 1; } }
  @keyframes briller {
    0%, 35% { stroke: #3a3531; filter: none; }
    62% { stroke: #f2ece2; filter: drop-shadow(0 0 10px rgb(229 85 159 / 0.9)); }
    80%, 100% { stroke: #fffaf2; filter: drop-shadow(0 0 26px rgb(242 236 226 / 0.95)) drop-shadow(0 0 60px rgb(229 85 159 / 0.9)); }
  }
  @keyframes illuminer {
    0%, 58% { transform: translate(-50%, -50%) scale(0); opacity: 0; }
    66% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
    100% { transform: translate(-50%, -50%) scale(7); opacity: 1; }
  }
  /* le noir se lève à la fin : la page apparaît dans la lumière */
  @keyframes lever { 0%, 76% { opacity: 1; } 100% { opacity: 0; } }
</style>
