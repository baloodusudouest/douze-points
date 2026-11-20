// 1.11.0 : les sons de la soirée, joués sur la télé seulement (écran du QR code, dévoilement) et sur l'appareil des
// Réglages (« Écouter »). Jamais importé par src/invite/ : les téléphones des invités restent muets (un test le vérifie).
//
// Choix de Julien (20/11/2026) : des sons fabriqués par le navigateur (Web Audio : oscillateurs, enveloppes, bruit
// filtré), aucun fichier ni droit ; chacun peut être remplacé par un fichier de l'hôte (Réglages › Dévoilement,
// rangé par le serveur sous /api/sons/<nom>). Avis du conseil 1.11.0 : neuf sons dans une même tonalité (ré majeur),
// un seul AudioContext créé au premier geste, un gain général (volume × muet), des rafales espacées d'au moins
// 90 ms, 6 voix au plus, resume() au retour sur l'onglet. Un fichier qui manque ou ne se lit pas : le son fabriqué,
// sans message.
//
// Emploi : installer() une fois (App.svelte, la régie) ; regler({ sons, volume_sons }) d'après les Réglages ;
// jouer(nom, { points }) ; boucle(nom) / arreter(nom) pour « attente » et « tambour » ; enchainer([...]) pour jouer
// des sons l'un après l'autre sur l'horloge audio (fanfare puis applaudissements) ; ecouter(fn) pour suivre l'état
// (bloqué, muet) ; ecouterSon(nom) pour « Écouter » dans les Réglages ; decoder(octets) pour vérifier un fichier.

export const NOMS = ['attente', 'carillon', 'tous_la', 'point', 'douze', 'tambour', 'depasse', 'fanfare', 'applaudissements']
export const LIBELLES = {
  attente: "Musique d'attente (écran du QR code)",
  carillon: 'Un invité arrive',
  tous_la: 'Tout le monde est là',
  point: 'Un pays reçoit ses points',
  douze: 'Douze points',
  tambour: 'Roulement de tambour (compte à rebours et remontée)',
  depasse: 'Un pays dépassé',
  fanfare: 'Fanfare du gagnant',
  applaudissements: 'Applaudissements',
}
const BOUCLES = new Set(['attente', 'tambour'])
const CLE_MUET = 'douze-points:muet'
const ECART = 0.09              // secondes entre deux sons d'une rafale
const VOIX_MAX = 6
const RE = 293.66               // ré 4 : la tonalité de tous les sons fabriqués
const PENTA = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21]       // ré majeur pentatonique, deux octaves
const freq = (demiTons, base = RE) => base * 2 ** (demiTons / 12)

let ctx = null                  // le seul AudioContext, créé au premier geste
let general = null              // gain général : volume × muet × réglage
let installe = false
let actifs = true               // Réglages › « Sons sur la télé »
let volume = 0.7
let muet = lireMuet()
let prochain = 0                // heure audio du prochain son permis (rafales espacées)
const voix = []                 // { fin, arret, boucle }
const fichiers = new Set()      // les sons remplacés par un fichier de l'hôte (liste du serveur)
const octets = new Map()        // nom → ArrayBuffer téléchargé (décodé une fois le contexte créé)
const tampons = new Map()       // nom → AudioBuffer, ou null si le fichier ne se lit pas
const boucles = new Map()       // nom → { arreter } en cours
const voulues = new Set()       // boucles demandées avant que le son soit permis : lancées au déblocage
const abonnes = new Set()
let bruitBlanc = null

function lireMuet() {
  try { return typeof localStorage !== 'undefined' && localStorage.getItem(CLE_MUET) === '1' } catch { return false }
}

function trace(nom) {
  // tests d'écran : la liste des sons demandés (jamais remplie en soirée)
  if (typeof window !== 'undefined' && Array.isArray(window.__DOUZE_POINTS_SONS)) window.__DOUZE_POINTS_SONS.push(nom)
}

// ---------------------------------------------------------------- état, pour le bouton haut-parleur
export function etat() {
  return { actifs, muet, bloque: !ctx || ctx.state !== 'running', volume }
}
function notifier() { const e = etat(); for (const f of abonnes) f(e) }
export function ecouter(fn) { abonnes.add(fn); fn(etat()); return () => abonnes.delete(fn) }

function appliquerGain() {
  if (!general) return
  const v = actifs && !muet ? volume : 0
  general.gain.setTargetAtTime(v, ctx.currentTime, 0.05)
}

export function regler({ sons, volume_sons } = {}) {
  if (typeof sons === 'boolean') actifs = sons
  if (typeof volume_sons === 'number') volume = Math.max(0, Math.min(100, volume_sons)) / 100
  if (!actifs) for (const nom of [...boucles.keys()]) arreterBoucle(nom)
  else relancer()
  appliquerGain()
  notifier()
  chargerFichiers()               // les écrans de la télé relisent la liste des fichiers de l'hôte en s'ouvrant
}

export function basculerMuet() {
  muet = !muet
  try { localStorage.setItem(CLE_MUET, muet ? '1' : '0') } catch { /* stockage fermé : le muet vaut pour la page */ }
  appliquerGain()
  notifier()
  return muet
}

// ---------------------------------------------------------------- le contexte audio
function creer() {
  if (ctx) return ctx
  const Classe = typeof window !== 'undefined' && (window.AudioContext || window.webkitAudioContext)
  if (!Classe) return null
  try { ctx = new Classe() } catch { ctx = null; return null }
  general = ctx.createGain()
  general.gain.value = actifs && !muet ? volume : 0
  general.connect(ctx.destination)
  ctx.onstatechange = () => { if (ctx.state === 'running') relancer(); notifier() }
  for (const nom of octets.keys()) decoderFichier(nom)
  return ctx
}

/** Un geste de l'utilisateur (clic, toucher, touche) : crée le contexte et le relance. */
export function debloquer() {
  if (!creer()) return
  if (ctx.state !== 'running') ctx.resume().then(() => { relancer(); notifier() }).catch(() => {})
  else relancer()
  notifier()
}

function relancer() {
  if (!ctx || ctx.state !== 'running') return
  for (const nom of voulues) if (!boucles.has(nom)) demarrerBoucle(nom)
}

export function installer() {
  if (installe || typeof window === 'undefined') return
  installe = true
  for (const type of ['pointerdown', 'keydown', 'touchend'])
    window.addEventListener(type, debloquer, { capture: true, passive: true })
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden && ctx && ctx.state !== 'running') ctx.resume().catch(() => {})
  })
  chargerFichiers()
}

/** Relit la liste des fichiers de l'hôte (après un remplacement dans les Réglages). */
export async function chargerFichiers() {
  try {
    const r = await fetch('/api/sons', { credentials: 'same-origin' })
    if (!r.ok) return
    const liste = await r.json()
    fichiers.clear()
    for (const s of liste) if (s.fichier) fichiers.add(s.nom)
    for (const nom of NOMS) if (!fichiers.has(nom)) { octets.delete(nom); tampons.delete(nom) }
    await Promise.all([...fichiers].map(telecharger))
  } catch { /* pas de serveur : les sons fabriqués */ }
}

export function oublier(nom) { octets.delete(nom); tampons.delete(nom) }

async function telecharger(nom) {
  if (octets.has(nom) || tampons.has(nom)) return
  try {
    const r = await fetch(`/api/sons/${nom}`, { credentials: 'same-origin' })
    if (!r.ok) { tampons.set(nom, null); return }
    octets.set(nom, await r.arrayBuffer())
    if (ctx) decoderFichier(nom)
  } catch { tampons.set(nom, null) }
}

function decoderFichier(nom) {
  const brut = octets.get(nom)
  if (!brut || !ctx) return
  octets.delete(nom)
  ctx.decodeAudioData(brut.slice(0)).then((b) => tampons.set(nom, b)).catch(() => tampons.set(nom, null))
}

/** Réglages : vérifie qu'un fichier se lit avant de l'envoyer (refusé sinon). Rend sa durée en secondes. */
export async function decoder(brut) {
  const Hors = window.OfflineAudioContext || window.webkitOfflineAudioContext
  const c = Hors ? new Hors(1, 1, 44100) : creer()
  if (!c) throw new Error('Ce navigateur ne lit pas les sons.')
  const b = await c.decodeAudioData(brut.slice(0))
  return b.duration
}

// ---------------------------------------------------------------- voix et rafales
function debut() {
  const t = Math.max(ctx.currentTime + 0.01, prochain)
  prochain = t + ECART
  return t
}

function prendreVoix(v) {
  const maintenant = ctx.currentTime
  for (let i = voix.length - 1; i >= 0; i--) if (!voix[i].boucle && voix[i].fin <= maintenant) voix.splice(i, 1)
  while (voix.length >= VOIX_MAX) {
    const i = voix.findIndex((x) => !x.boucle)
    if (i < 0) return false
    const [vieille] = voix.splice(i, 1)
    try { vieille.arret() } catch { /* déjà fini */ }
  }
  voix.push(v)
  return true
}

function sortie(t, force = false) {
  // « Écouter » (force) passe à côté du gain général (muet, sons coupés) mais garde le volume réglé
  const g = ctx.createGain()
  g.gain.setValueAtTime(force ? volume : 1, t)
  g.connect(force ? ctx.destination : general)
  return g
}

function note(dest, t, f, duree, { type = 'sine', niveau = 0.3, attaque = 0.01, detune = 0 } = {}) {
  const o = ctx.createOscillator(), g = ctx.createGain()
  o.type = type
  o.frequency.setValueAtTime(f, t)
  if (detune) o.detune.setValueAtTime(detune, t)
  g.gain.setValueAtTime(0.0001, t)
  g.gain.exponentialRampToValueAtTime(niveau, t + attaque)
  g.gain.exponentialRampToValueAtTime(0.0001, t + duree)
  o.connect(g).connect(dest)
  o.start(t)
  o.stop(t + duree + 0.05)
  return o
}

function bruit() {
  if (bruitBlanc) return bruitBlanc
  const n = ctx.sampleRate * 2
  bruitBlanc = ctx.createBuffer(1, n, ctx.sampleRate)
  const d = bruitBlanc.getChannelData(0)
  for (let i = 0; i < n; i++) d[i] = Math.random() * 2 - 1
  return bruitBlanc
}

// ---------------------------------------------------------------- les sons fabriqués (une seule tonalité : ré)
// Chacun reçoit sa sortie (gain branché sur le gain général) et l'heure de départ ; il rend sa durée.
const FABRIQUES = {
  carillon(dest, t) {
    // deux cloches : la 5, puis ré 6
    for (const [k, f] of [[0, freq(19)], [0.16, freq(24)]]) {
      note(dest, t + k, f, 1.4, { niveau: 0.22, attaque: 0.005 })
      note(dest, t + k, f * 2.76, 0.6, { niveau: 0.05, attaque: 0.005 })
    }
    return 1.6
  },
  tous_la(dest, t) {
    // l'accord de ré majeur, posé doucement, puis l'octave
    ;[0, 4, 7, 12].forEach((s, i) => note(dest, t + i * 0.07, freq(s), 2.4, { type: 'triangle', niveau: 0.12, attaque: 0.08 }))
    note(dest, t + 0.35, freq(24), 1.8, { niveau: 0.08, attaque: 0.02 })
    return 2.6
  },
  point(dest, t, { points = 1 } = {}) {
    // la hauteur monte avec les points, sur la gamme pentatonique de ré
    const s = PENTA[degre(points)]
    note(dest, t, freq(s + 12), 0.45, { type: 'triangle', niveau: 0.26, attaque: 0.005 })
    note(dest, t, freq(s + 24), 0.25, { niveau: 0.07, attaque: 0.005 })
    return 0.5
  },
  douze(dest, t) {
    // un arpège vif ré – fa# – la – ré, puis l'accord qui brille
    ;[12, 16, 19, 24].forEach((s, i) => note(dest, t + i * 0.07, freq(s), 0.5, { type: 'square', niveau: 0.06, attaque: 0.005 }))
    ;[12, 16, 19, 24, 28].forEach((s) => note(dest, t + 0.3, freq(s), 1.3, { type: 'triangle', niveau: 0.1, attaque: 0.01 }))
    return 1.6
  },
  depasse(dest, t) {
    // un petit glissé vers le haut (la 5 → ré 6)
    const o = ctx.createOscillator(), g = ctx.createGain()
    o.type = 'triangle'
    o.frequency.setValueAtTime(freq(19), t)
    o.frequency.exponentialRampToValueAtTime(freq(24), t + 0.12)
    g.gain.setValueAtTime(0.0001, t)
    g.gain.exponentialRampToValueAtTime(0.2, t + 0.01)
    g.gain.exponentialRampToValueAtTime(0.0001, t + 0.22)
    o.connect(g).connect(dest)
    o.start(t); o.stop(t + 0.25)
    return 0.25
  },
  fanfare(dest, t) {
    // le motif du prélude du Te Deum de Charpentier (domaine public), en ré majeur, joué par des oscillateurs
    // (cuivres : dents de scie filtrées, doublées à l'octave ; timbales ré–la)
    const noire = 0.32
    const motif = [            // [demi-tons depuis ré 4, durée en noires]
      [-5, 0.5], [0, 1], [0, 0.75], [2, 0.25], [4, 0.5], [0, 0.5], [7, 1.5], [4, 0.5],
      [5, 0.5], [7, 0.5], [5, 0.5], [4, 0.5], [2, 1], [0, 2],
    ]
    const filtre = ctx.createBiquadFilter()
    filtre.type = 'lowpass'
    filtre.frequency.setValueAtTime(2600, t)
    filtre.connect(dest)
    let k = t
    for (const [s, d] of motif) {
      const duree = d * noire
      note(filtre, k, freq(s + 12), duree * 0.95, { type: 'sawtooth', niveau: 0.09, attaque: 0.03 })
      note(filtre, k, freq(s), duree * 0.95, { type: 'sawtooth', niveau: 0.05, attaque: 0.03, detune: 6 })
      k += duree
    }
    for (const [quand, f] of [[0, freq(-24)], [noire * 0.5, freq(-17)], [noire * 1.5, freq(-24)], [k - t - noire * 2, freq(-24)]]) {
      const o = ctx.createOscillator(), g = ctx.createGain()
      o.frequency.setValueAtTime(f * 1.5, t + quand)
      o.frequency.exponentialRampToValueAtTime(f, t + quand + 0.08)
      g.gain.setValueAtTime(0.0001, t + quand)
      g.gain.exponentialRampToValueAtTime(0.35, t + quand + 0.01)
      g.gain.exponentialRampToValueAtTime(0.0001, t + quand + 0.7)
      o.connect(g).connect(dest)
      o.start(t + quand); o.stop(t + quand + 0.75)
    }
    return k - t + 0.2
  },
  applaudissements(dest, t) {
    // du bruit modulé : des centaines de claquements brefs, qui montent puis s'éteignent
    const duree = 4.5, sr = ctx.sampleRate, n = Math.floor(sr * duree)
    const b = ctx.createBuffer(1, n, sr), d = b.getChannelData(0)
    for (let c = 0; c < 520; c++) {
      const x = Math.random()
      const ou = Math.floor((x < 0.8 ? x / 0.8 * 0.6 : 0.6 + (x - 0.8) / 0.2 * 0.4) * (n - sr * 0.03))
      const fort = 0.25 + Math.random() * 0.75, long = Math.floor(sr * (0.008 + Math.random() * 0.012))
      for (let i = 0; i < long; i++) d[ou + i] += (Math.random() * 2 - 1) * fort * Math.exp(-i / (long / 4))
    }
    const src = ctx.createBufferSource(), passe = ctx.createBiquadFilter(), g = ctx.createGain()
    src.buffer = b
    passe.type = 'bandpass'; passe.frequency.setValueAtTime(1800, t); passe.Q.setValueAtTime(0.6, t)
    g.gain.setValueAtTime(0.0001, t)
    g.gain.exponentialRampToValueAtTime(0.5, t + 0.4)
    g.gain.setValueAtTime(0.5, t + duree - 1.5)
    g.gain.exponentialRampToValueAtTime(0.0001, t + duree)
    src.connect(passe).connect(g).connect(dest)
    src.start(t); src.stop(t + duree)
    return duree
  },
}

function degre(points) {
  return Math.max(0, Math.min(PENTA.length - 1, Math.round(Math.log2(1 + Math.max(0, points)) * 2)))
}

// ---------------------------------------------------------------- jouer
function peutJouer(force) {
  if (!force && (!actifs || muet)) return false
  if (!ctx) creer()
  return !!ctx && ctx.state === 'running'
}

/** Joue un son une fois. options.points : les points d'un pays (« point »). Rend la durée (s), ou 0. */
export function jouer(nom, options = {}) {
  trace(nom)
  if (!NOMS.includes(nom) || BOUCLES.has(nom) || !peutJouer(options.force)) return 0
  return lancer(nom, options.quand ?? debut(), options)
}

function lancer(nom, t, options = {}) {
  const dest = sortie(t, !!options.force)
  const tampon = tampons.get(nom)
  let duree
  if (tampon) {
    const src = ctx.createBufferSource()
    src.buffer = tampon
    if (nom === 'point') src.playbackRate.setValueAtTime(2 ** (PENTA[degre(options.points ?? 1)] / 12), t)
    src.connect(dest)
    src.start(t)
    duree = tampon.duration / (src.playbackRate.value || 1)
  } else duree = FABRIQUES[nom](dest, t, options)
  prendreVoix({ fin: t + duree, boucle: false, arret: () => dest.disconnect() })
  return duree
}

/** Joue des sons l'un après l'autre, sur l'horloge audio (aucun minuteur) : enchainer(['fanfare', 'applaudissements']). */
export function enchainer(noms) {
  noms.forEach(trace)
  if (!peutJouer(false)) return
  let t = debut()
  for (const nom of noms) t += Math.max(0.1, lancer(nom, t)) - 0.15
}

/** Réglages › « Écouter » : joue le son même si les sons de la télé sont coupés (au volume réglé). */
export function ecouterSon(nom) {
  debloquer()
  trace(nom)
  if (!ctx) return 0
  const t = debut()
  if (BOUCLES.has(nom)) {
    // un extrait de 4 s de la boucle
    const b = construireBoucle(nom, t, true)
    if (b) setTimeout(() => b.arreter(), 4000)
    return 4
  }
  return lancer(nom, t, { force: true, points: 12 })
}

// ---------------------------------------------------------------- les boucles : attente, tambour
export function boucle(nom) {
  trace(nom)
  if (!BOUCLES.has(nom)) return
  voulues.add(nom)
  if (!boucles.has(nom) && peutJouer(false)) demarrerBoucle(nom)
}

export function arreter(nom) {
  voulues.delete(nom)
  arreterBoucle(nom)
}

export function arreterTout() {
  for (const nom of [...voulues]) arreter(nom)
}

function arreterBoucle(nom) {
  const b = boucles.get(nom)
  if (b) { boucles.delete(nom); b.arreter() }
}

function demarrerBoucle(nom) {
  if (!actifs || !ctx || ctx.state !== 'running') return
  const b = construireBoucle(nom, ctx.currentTime + 0.02, false)
  if (b) boucles.set(nom, b)
}

function construireBoucle(nom, t, force) {
  const dest = sortie(t, force)
  const tampon = tampons.get(nom)
  let fin
  if (tampon) {
    const src = ctx.createBufferSource()
    src.buffer = tampon; src.loop = true
    src.connect(dest); src.start(t)
    fin = () => src.stop()
  } else fin = nom === 'tambour' ? tambour(dest, t) : attente(dest, t)
  const v = { fin: Infinity, boucle: true, arret: () => {} }
  voix.push(v)
  return {
    arreter() {
      const maintenant = ctx.currentTime
      dest.gain.cancelScheduledValues(maintenant)
      dest.gain.setValueAtTime(dest.gain.value, maintenant)
      dest.gain.linearRampToValueAtTime(0, maintenant + 0.25)
      setTimeout(() => { try { fin() } catch { /* déjà arrêté */ } dest.disconnect() }, 400)
      const i = voix.indexOf(v)
      if (i >= 0) voix.splice(i, 1)
    },
  }
}

function tambour(dest, t) {
  // le roulement : du bruit filtré, battu ~18 fois par seconde, qui monte (plus fort, plus clair) en 25 s
  const src = ctx.createBufferSource(), filtre = ctx.createBiquadFilter(), bat = ctx.createGain(), monte = ctx.createGain()
  const lfo = ctx.createOscillator(), profondeur = ctx.createGain()
  src.buffer = bruit(); src.loop = true
  filtre.type = 'bandpass'; filtre.Q.setValueAtTime(0.9, t)
  filtre.frequency.setValueAtTime(700, t); filtre.frequency.linearRampToValueAtTime(2200, t + 25)
  lfo.type = 'sine'; lfo.frequency.setValueAtTime(15, t); lfo.frequency.linearRampToValueAtTime(21, t + 25)
  bat.gain.setValueAtTime(0.55, t); profondeur.gain.setValueAtTime(0.45, t)
  lfo.connect(profondeur).connect(bat.gain)
  monte.gain.setValueAtTime(0.0001, t)
  monte.gain.exponentialRampToValueAtTime(0.12, t + 0.6)
  monte.gain.linearRampToValueAtTime(0.42, t + 25)
  src.connect(filtre).connect(bat).connect(monte).connect(dest)
  // une timbale grave sur le ré, toutes les 2 s, pour tenir le tout
  const grave = ctx.createOscillator(), gg = ctx.createGain()
  grave.frequency.setValueAtTime(freq(-24), t)
  gg.gain.setValueAtTime(0.0001, t)
  gg.gain.exponentialRampToValueAtTime(0.1, t + 1)
  gg.gain.linearRampToValueAtTime(0.22, t + 25)
  grave.connect(gg).connect(dest)
  src.start(t); lfo.start(t); grave.start(t)
  return () => { src.stop(); lfo.stop(); grave.stop() }
}

function attente(dest, t) {
  // un arpège lent et doux (ré – la – fa# – la, puis si – fa# – ré – fa#…), plus bas que le reste ; planifié par
  // petites avances sur l'horloge audio
  const suite = [0, 7, 4, 7, -3, 4, 0, 4, -5, 2, -1, 2, -3, 4, 1, 4]
  const pas = 0.62
  let k = 0, prochaineNote = t, ouvert = true
  const doux = ctx.createGain()
  doux.gain.setValueAtTime(0.0001, t)
  doux.gain.exponentialRampToValueAtTime(0.35, t + 1.5)
  doux.connect(dest)
  const planifier = () => {
    if (!ouvert) return
    while (prochaineNote < ctx.currentTime + 1.2) {
      const s = suite[k % suite.length]
      note(doux, prochaineNote, freq(s - 12), pas * 2.4, { niveau: 0.16, attaque: 0.06 })
      if (k % 4 === 0) note(doux, prochaineNote, freq(s - 24), pas * 4, { type: 'triangle', niveau: 0.08, attaque: 0.2 })
      prochaineNote += pas
      k++
    }
  }
  planifier()
  const minuterie = setInterval(planifier, 300)
  return () => { ouvert = false; clearInterval(minuterie) }
}
