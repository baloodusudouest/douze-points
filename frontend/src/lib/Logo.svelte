<script>
  // Le logo de Douze points : le « 12 » sous un projecteur. Sa hauteur suit la taille du texte (1em = hauteur).
  // `eteint` : le 12 en gris, sans lumière (avant que la soirée démarre).
  let { class: classe = '', eteint = false } = $props()
</script>

<svg viewBox="0 0 120 100" class={classe} style="height: 1em; width: 1.2em; overflow: visible" role="img" aria-label="Douze points">
  <defs>
    <linearGradient id="faisceau" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#e5559f" stop-opacity="0.6" /><stop offset="1" stop-color="#e5559f" stop-opacity="0.04" />
    </linearGradient>
  </defs>
  {#if !eteint}
    <path d="M52 -14h16l46 112H6z" fill="url(#faisceau)" />
    <ellipse cx="60" cy="92" rx="50" ry="7" fill="#e5559f" opacity="0.2" />
  {/if}
  <g fill="none" stroke={eteint ? '#3a3531' : '#f2ece2'} stroke-width="6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M28 34l15-11v60" />
    <path d="M62 38c0-9.500 7-16 16-16s16 6.500 16 15.500c0 7.500-4.500 12.500-12.500 20L62 82h33" />
  </g>
</svg>
