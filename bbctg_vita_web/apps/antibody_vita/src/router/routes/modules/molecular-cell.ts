import type { RouteRecordRaw } from 'vue-router';

const LIBRARY_TAB_GROUP = '/molecular-cell/library-construction';

const routes: RouteRecordRaw[] = [
  {
    meta: {
      authority: ['molecular.page.library'],
      featureCode: 'menu.molecular_cell',
      icon: 'lucide:dna',
      order: 30,
      title: '分子与细胞',
    },
    name: 'MolecularCell',
    path: '/molecular-cell',
    redirect: '/molecular-cell/library-construction',
    children: [
      {
        name: 'LibraryConstructionList',
        path: '/molecular-cell/library-construction',
        component: () => import('#/views/MolecularCell/library/LibraryConstructionList.vue'),
        meta: {
          authority: ['molecular.page.library'],
          featureCode: 'menu.molecular_cell.library',
          icon: 'lucide:library',
          keepAlive: true,
          order: 5,
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
    ],
  },
];

export default routes;
