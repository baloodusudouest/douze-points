import { mount } from 'svelte'
import '@fontsource-variable/inter'
import './app.css'
import App from './App.svelte'
import Invite from './invite/Invite.svelte'

// Deux applis dans une : la régie (mot de passe commun) et la porte invité (/invite/<jeton>, sans mot de passe).
const invite = location.pathname.match(/^\/invite\/([^/]+)/)
export default invite
  ? mount(Invite, { target: document.getElementById('app'), props: { jeton: invite[1] } })
  : mount(App, { target: document.getElementById('app') })
