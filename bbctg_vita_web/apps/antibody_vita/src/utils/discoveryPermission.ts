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

export function canAffinityEditDiscoverySynthesis(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.synthesis_progress.affinity_edit');
}

export function canFlowEditDiscoverySynthesis(userInfo: any): boolean {
  return hasAccessCode(userInfo, 'discovery.synthesis_progress.flow_edit');
}
