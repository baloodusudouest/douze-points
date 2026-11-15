// Le drapeau d'un pays à partir de son nom en français (émoji : deux lettres « indicateur régional »).
// Un pays absent de la table n'a pas de drapeau, c'est tout : rien n'est inventé.
const CODES = {
  albanie: 'AL', allemagne: 'DE', andorre: 'AD', armenie: 'AM', australie: 'AU', autriche: 'AT', azerbaidjan: 'AZ',
  belgique: 'BE', bielorussie: 'BY', 'bosnie-herzegovine': 'BA', bulgarie: 'BG', chypre: 'CY', croatie: 'HR',
  danemark: 'DK', espagne: 'ES', estonie: 'EE', finlande: 'FI', france: 'FR', georgie: 'GE', grece: 'GR',
  hongrie: 'HU', irlande: 'IE', islande: 'IS', israel: 'IL', italie: 'IT', kazakhstan: 'KZ', kosovo: 'XK',
  lettonie: 'LV', lituanie: 'LT', luxembourg: 'LU', 'macedoine du nord': 'MK', malte: 'MT', maroc: 'MA',
  moldavie: 'MD', monaco: 'MC', montenegro: 'ME', norvege: 'NO', 'pays-bas': 'NL', pologne: 'PL', portugal: 'PT',
  roumanie: 'RO', 'royaume-uni': 'GB', russie: 'RU', 'saint-marin': 'SM', serbie: 'RS', slovaquie: 'SK',
  slovenie: 'SI', suede: 'SE', suisse: 'CH', tchequie: 'CZ', 'republique tcheque': 'CZ', turquie: 'TR', ukraine: 'UA',
  bangladesh: 'BD', bhoutan: 'BT', cambodge: 'KH', chine: 'CN', 'coree du sud': 'KR', inde: 'IN', indonesie: 'ID',
  japon: 'JP', laos: 'LA', malaisie: 'MY', mongolie: 'MN', nepal: 'NP', philippines: 'PH', singapour: 'SG',
  'sri lanka': 'LK', thailande: 'TH', vietnam: 'VN', 'viet nam': 'VN',
}

const cle = (nom) => (nom || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/['’]/g, ' ').trim()

export function drapeau(pays, code) {
  const c = (code || CODES[cle(pays)] || '').toUpperCase()
  if (!/^[A-Z]{2}$/.test(c)) return ''
  return String.fromCodePoint(...[...c].map((l) => 0x1f1e6 + l.charCodeAt(0) - 65))
}

export const EMISSIONS = { demi1: 'Première demi-finale', demi2: 'Seconde demi-finale', finale: 'Finale', unique: 'Soirée unique' }
export const BAREME = [12, 10, 8, 7, 6, 5, 4, 3, 2, 1]
// 13.5 → « 13,5 » ; 12 → « 12 »
export const note = (v) => (v == null ? '' : String(v).replace('.', ','))

// Le titre fabriqué d'une soirée : « Eurovision Burgas 2027, finale ». Même règle que titre_evenement (app/main.py).
const LIBELLES = { demi1: 'première demi-finale', demi2: 'seconde demi-finale', finale: 'finale', unique: '' }
export function titreEvenement({ concours, annee, emission, ville }) {
  const debut = [concours, (ville || '').trim(), annee].filter(Boolean).join(' ')
  return LIBELLES[emission] ? `${debut}, ${LIBELLES[emission]}` : debut
}

// Une liste collée telle quelle depuis un site de fans arrive souvent en un seul morceau :
// « 🇧🇹 Bhutan: Artiste - Titre ». normaliser() en tire le drapeau, le pays, l'artiste et le titre,
// pour l'affichage. Même règle côté serveur, pour les listes collées à partir de la 0.8 (lire_collage).
const DRAPEAU_EN_TETE = /^\s*([\u{1F1E6}-\u{1F1FF}]{2})\s*/u
export function normaliser(c) {
  let { pays = '', artiste = '', titre = '', code_pays = '' } = c
  const m = pays.match(DRAPEAU_EN_TETE)
  if (m) {
    code_pays = code_pays || [...m[1]].map((l) => String.fromCharCode(l.codePointAt(0) - 0x1f1e6 + 65)).join('')
    pays = pays.slice(m[0].length)
  }
  if (!artiste && !titre) {
    const i = pays.indexOf(': ')
    if (i > 0) {
      const suite = pays.slice(i + 2)
      pays = pays.slice(0, i)
      const j = suite.indexOf(' - ')
      if (j > 0) { artiste = suite.slice(0, j); titre = suite.slice(j + 3) } else artiste = suite
    }
  }
  return { ...c, pays: pays.trim(), artiste: artiste.trim(), titre: titre.trim(), code_pays }
}
