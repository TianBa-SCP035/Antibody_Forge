import type { RouteRecordRaw } from 'vue-router';

const LIBRARY_TAB_GROUP = '/molecular-cell/library-construction';
const TRANSFECTION_TAB_GROUP = '/molecular-cell/transfection';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['molecular.page.library', 'molecular.page.primer', 'molecular.page.transfection'],
      featureCode: 'menu.molecular_cell',
      icon: 'lucide:dna',
      order: 30,
      title: '分子与细胞',
    },
    name: 'MolecularCell',
    path: '/molecular-cell',
    redirect: '/molecular-cell/primer-library',
    children: [
      {
        name: 'PrimerLibrary',
        path: '/molecular-cell/primer-library',
        component: () => import('#/views/MolecularCell/primer/PrimerLibrary.vue'),
        meta: {
          authority: ['molecular.page.primer'],
          featureCode: 'menu.molecular_cell.primer',
          icon: 'lucide:flask-conical',
          order: 5,
          title: '引物库',
        },
      },
      {
        name: 'LibraryConstructionList',
        path: '/molecular-cell/library-construction',
        component: () => import('#/views/MolecularCell/library/LibraryConstructionList.vue'),
        meta: {
          authority: ['molecular.page.library'],
          featureCode: 'menu.molecular_cell.library',
          fullPathKey: false,
          icon: 'lucide:library',
          keepAlive: true,
          order: 10,
          tabGroup: LIBRARY_TAB_GROUP,
          title: '文库构建',
        },
      },
      {
        name: 'LibraryConstructionResult',
        path: '/molecular-cell/library-construction/result',
        component: () => import('#/views/MolecularCell/library/LibraryConstructionResult.vue'),
        meta: {
          authority: ['molecular.page.library_detail'],
          hideInMenu: true,
          icon: 'lucide:file-text',
          fullPathKey: false,
          keepAlive: true,
          activePath: LIBRARY_TAB_GROUP,
          tabGroup: LIBRARY_TAB_GROUP,
          title: '文库质控',
        },
      },
      {
        name: 'TransfectionList',
        path: '/molecular-cell/transfection',
        component: () => import('#/views/MolecularCell/transfection/TransfectionList.vue'),
        meta: {
          authority: ['molecular.page.transfection'],
          featureCode: 'menu.molecular_cell.transfection',
          fullPathKey: false,
          icon: 'lucide:test-tubes',
          keepAlive: true,
          order: 20,
          tabGroup: TRANSFECTION_TAB_GROUP,
          title: '转染与表达',
        },
      },
      {
        name: 'TransfectionProteins',
        path: '/molecular-cell/transfection/proteins',
        component: () => import('#/views/MolecularCell/transfection/TransfectionProteins.vue'),
        meta: {
          authority: ['molecular.page.transfection'],
          hideInMenu: true,
          icon: 'lucide:table',
          fullPathKey: false,
          keepAlive: true,
          activePath: TRANSFECTION_TAB_GROUP,
          tabGroup: TRANSFECTION_TAB_GROUP,
          title: '转染表',
        },
      },
    ],
  },
];

export default routes;
