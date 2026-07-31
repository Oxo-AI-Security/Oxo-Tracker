import { shallowRef, type ShallowRef } from 'vue'

export interface AppBreadcrumbDefinition {
  label: string
  labelKey?: string
  to?: string
  param?: string
  prefix?: string
}

export interface AppBreadcrumbOverride {
  owner: string
  breadcrumbs: AppBreadcrumbDefinition[]
  pathPrefix?: string
}

const breadcrumbOverride = shallowRef<AppBreadcrumbOverride | null>(null)

export function useAppBreadcrumbOverride(): ShallowRef<AppBreadcrumbOverride | null> {
  return breadcrumbOverride
}

export function setAppBreadcrumbs(
  owner: string,
  breadcrumbs: AppBreadcrumbDefinition[],
  pathPrefix?: string,
) {
  breadcrumbOverride.value = {
    owner,
    breadcrumbs: [...breadcrumbs],
    pathPrefix,
  }
}

export function matchesAppBreadcrumbOverride(
  override: AppBreadcrumbOverride | null,
  currentPath: string,
) {
  return Boolean(
    override
    && (!override.pathPrefix || currentPath.startsWith(override.pathPrefix)),
  )
}

export function clearAppBreadcrumbs(owner: string) {
  if (breadcrumbOverride.value?.owner === owner) {
    breadcrumbOverride.value = null
  }
}
