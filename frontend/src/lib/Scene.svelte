<script>
  // La scène : une rampe de cinq projecteurs dont les faisceaux balaient lentement, sans jamais s'arrêter,
  // et le « 12 » au centre, dans leur lumière. Bannière du haut de l'écran d'accueil d'une soirée.
  // Si l'appareil demande moins d'animations, les faisceaux restent fixes.
  const lampes = [
    // angle d'un faisceau : négatif, il penche vers la droite ; les lampes de gauche visent donc le 12 au centre
    { x: 190, de: -74, a: -42, duree: 13, retard: -2 },
    { x: 305, de: -62, a: -22, duree: 17, retard: -7 },
    { x: 400, de: -14, a: 14, duree: 11, retard: -4 },
    { x: 495, de: 22, a: 62, duree: 19, retard: -11 },
    { x: 610, de: 42, a: 74, duree: 15, retard: -5 },
  ]
</script>

<!-- Cadrage : la bannière est tantôt très large (iPhone en paysage), tantôt plus haute (téléphone debout).
     Le dessin est rogné pour remplir ; tout ce qui compte (rampe, 12, sol) tient dans la bande centrale. -->
<svg viewBox="0 0 800 130" preserveAspectRatio="xMidYMid slice" role="img" aria-label="Douze points" class="scene">
  <defs>
    <linearGradient id="s-faisceau" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e5559f" stop-opacity="0.7" /><stop offset="1" stop-color="#e5559f" stop-opacity="0" />
    </linearGradient>
    <linearGradient id="s-clair" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#f2ece2" stop-opacity="0.5" /><stop offset="1" stop-color="#f2ece2" stop-opacity="0" />
    </linearGradient>
    <radialGradient id="s-sol" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#e5559f" stop-opacity="0.45" /><stop offset="1" stop-color="#e5559f" stop-opacity="0" />
    </radialGradient>
  </defs>
  <rect x="-400" width="1600" height="130" fill="#0f0d0c" />
  <ellipse cx="400" cy="106" rx="210" ry="13" fill="url(#s-sol)" class="sol" />
  {#each lampes as l, i}
    <g class="faisceau" style="transform-origin: {l.x}px 20px; --de: {l.de}deg; --a: {l.a}deg; animation-duration: {l.duree}s; animation-delay: {l.retard}s">
      <path d="M{l.x - 5} 20h10l40 250H{l.x - 45}z" fill={i % 2 ? 'url(#s-clair)' : 'url(#s-faisceau)'} />
    </g>
  {/each}
  <!-- la rampe et ses lampes -->
  <rect x="-400" y="17" width="1600" height="2" fill="#312c27" />
  {#each lampes as l}<rect x={l.x - 7} y="15" width="14" height="8" rx="2.500" fill="#3a3531" />{/each}
  <g class="douze" fill="none" stroke="#f2ece2" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"
     transform="translate(400 70) scale(0.6) translate(-406 -126)">
    <path d="M352 96l24-18v96" />
    <path d="M408 102c0-15 11-25.500 26-25.500s26 10.500 26 25c0 12-7.500 20-20.500 32.500L408 172.500h53" />
  </g>
</svg>

<style>
  .scene { display: block; width: 100%; height: 100%; }
  .faisceau { transform-box: view-box; mix-blend-mode: screen; opacity: 0.75; animation: balayer ease-in-out infinite alternate; }
  .douze { animation: luire 6s ease-in-out infinite alternate; }
  .sol { animation: respirer 9s ease-in-out infinite alternate; }
  @keyframes balayer { from { transform: rotate(var(--de)); } to { transform: rotate(var(--a)); } }
  @keyframes luire {
    from { filter: drop-shadow(0 0 5px rgb(229 85 159 / 0.55)); }
    to { filter: drop-shadow(0 0 14px rgb(242 236 226 / 0.75)) drop-shadow(0 0 30px rgb(229 85 159 / 0.7)); }
  }
  @keyframes respirer { from { opacity: 0.6; } to { opacity: 1; } }
  @media (prefers-reduced-motion: reduce) {
    .faisceau, .douze, .sol { animation: none; }
    .faisceau { transform: rotate(calc((var(--de) + var(--a)) / 2)); }
  }
</style>
