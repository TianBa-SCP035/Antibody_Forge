export type FeatureState = {
  code: string;
  enabled: boolean;
  sort_order?: number;
  visible: boolean;
};

export interface FeatureFilterState {
  stateMap: Map<string, FeatureState>;
  treatMissingFeatureAsHidden: boolean;
}

let cachedFeatureFilter: FeatureFilterState | null = null;

export function setCachedFeatureFilter(
  stateMap: Map<string, FeatureState>,
  treatMissingFeatureAsHidden: boolean,
) {
  cachedFeatureFilter = {
    stateMap: new Map(stateMap),
    treatMissingFeatureAsHidden,
  };
}

export function getCachedFeatureFilter(): FeatureFilterState | null {
  return cachedFeatureFilter;
}

export function filterRouteTree(
  routes: any[],
  stateMap: Map<string, FeatureState>,
  treatMissingFeatureAsHidden: boolean,
): any[] {
  return routes
    .map((route) => {
      const featureCode = route.meta?.featureCode;
      const state = featureCode ? stateMap.get(featureCode) : undefined;
      const children = route.children
        ? filterRouteTree(route.children, stateMap, treatMissingFeatureAsHidden)
        : route.children;
      return {
        ...route,
        children,
        meta: {
          ...route.meta,
          order: state?.sort_order ?? route.meta?.order,
        },
      };
    })
    .filter((route) => {
      const featureCode = route.meta?.featureCode;
      if (!featureCode) {
        return route.children === undefined || route.children.length > 0;
      }
      const state = stateMap.get(featureCode);
      if (treatMissingFeatureAsHidden && !state) return false;
      if (state && (!state.enabled || !state.visible)) return false;
      return route.children === undefined || route.children.length > 0;
    });
}
