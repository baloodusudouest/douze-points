<script>
  // Le drapeau en image (paquet flag-icons, licence MIT), pour la fiche et son impression : Windows n'affiche
  // pas les drapeaux en émoji (il écrit « FR », « PH »…). Chaque image n'est chargée que si elle sert.
  import { codePays } from '$lib/pays.js'
  const IMAGES = import.meta.glob('/node_modules/flag-icons/flags/4x3/*.svg', { eager: true, query: '?url', import: 'default' })
  let { pays = '', code = '' } = $props()
  let c = $derived(codePays(pays, code).toLowerCase())
  let src = $derived(c ? IMAGES[`/node_modules/flag-icons/flags/4x3/${c}.svg`] : null)
</script>

{#if src}<img {src} alt="" class="drapeau-image" width="20" height="15" />{/if}

<style>
  .drapeau-image { display: inline-block; width: 1.25em; height: 0.94em; margin-right: 0.3em; vertical-align: -0.1em;
    border-radius: 2px; box-shadow: 0 0 0 0.5px rgb(0 0 0 / 0.25); object-fit: cover; }
</style>
