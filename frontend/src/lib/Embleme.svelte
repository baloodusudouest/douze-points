<script>
  // L'emblème de la soirée : le logo déposé par l'hôte s'il y en a un, sinon le « 12 » sous un projecteur.
  // La hauteur suit la taille du texte (1em), comme Logo.
  import Logo from './Logo.svelte'
  let { src = null } = $props()
</script>

{#if src}
  <img {src} alt="Logo de l'évènement" style="height: 1em; width: auto; max-width: 100%; object-fit: contain" />
{:else}
  <Logo />
{/if}
