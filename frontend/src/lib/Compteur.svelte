<script>
  // Un nombre qui compte jusqu'à sa nouvelle valeur au lieu de sauter (les points qui s'additionnent).
  import { Tween, prefersReducedMotion } from 'svelte/motion'
  import { cubicOut } from 'svelte/easing'
  let { valeur, depart = null, duree = 900, retard = 0 } = $props()
  const nombre = new Tween(depart ?? valeur, { easing: cubicOut })
  $effect(() => {
    const calme = prefersReducedMotion.current
    nombre.set(valeur, { duration: calme ? 0 : duree, delay: calme ? 0 : retard })
  })
</script>

{Math.round(nombre.current)}
