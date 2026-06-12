import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import GroupsView from '../views/GroupsView.vue'
import PredictView from '../views/PredictView.vue'
import TournamentView from '../views/TournamentView.vue'
import MarketsView from '../views/MarketsView.vue'
import LegalNoticeView from '../views/LegalNoticeView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: Home },
    { path: '/groups', component: GroupsView },
    { path: '/predict', component: PredictView },
    { path: '/tournament', component: TournamentView },
    { path: '/markets', component: MarketsView },
    { path: '/legal', component: LegalNoticeView },
  ]
})
