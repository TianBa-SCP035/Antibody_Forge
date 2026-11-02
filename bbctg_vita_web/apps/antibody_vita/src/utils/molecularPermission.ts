import { hasAccessCode } from '#/utils/accessCode';

export function canViewLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.page.library');
}

export function canViewLibraryDetail(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.page.library_detail');
}

export function canEditLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.library.edit');
}

export function canEditPrimerLibrary(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.primer.edit');
}

export function canManageLibraryFiles(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'molecular.library.file.manage');
}

export function canHandoffLibrary(userInfo: any): boolean {
  return (
    hasAccessCode(userInfo, 'discovery.workbench.edit')
    || hasAccessCode(userInfo, 'molecular.library.edit')
  );
}
