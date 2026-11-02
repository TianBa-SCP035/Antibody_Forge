import { hasAccessCode } from '#/utils/accessCode';

export function canEditDiscoveryWorkbench(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.workbench.edit');
}

export function canEditDiscoverySynthesis(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.synthesis_progress.edit');
}

export function canPmEditDiscoverySynthesis(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.synthesis_progress.pm_edit');
}

export function canAssayEditDiscoverySynthesis(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.synthesis_progress.assay_edit');
}
