"use client"

export const SELECTED_ORGANIZATION_STORAGE_KEY = "selected_organization"
const LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY = "selectedOrganization"
const SELECTED_ORGANIZATION_EVENT = "selected-organization-change"

function writeSelectedOrganization(value: string | null) {
  if (typeof window === "undefined") return

  if (value) {
    localStorage.setItem(SELECTED_ORGANIZATION_STORAGE_KEY, value)
    localStorage.setItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY, value)
  } else {
    localStorage.removeItem(SELECTED_ORGANIZATION_STORAGE_KEY)
    localStorage.removeItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY)
  }
}

export function getStoredSelectedOrganization(): string | null {
  if (typeof window === "undefined") return null

  const value =
    localStorage.getItem(SELECTED_ORGANIZATION_STORAGE_KEY) ||
    localStorage.getItem(LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY)

  if (value) {
    writeSelectedOrganization(value)
  }

  return value
}

export function setStoredSelectedOrganization(value: string | null) {
  if (typeof window === "undefined") return

  writeSelectedOrganization(value)
  window.dispatchEvent(
    new CustomEvent(SELECTED_ORGANIZATION_EVENT, {
      detail: { value },
    })
  )
}

export function subscribeToSelectedOrganization(callback: (value: string | null) => void) {
  if (typeof window === "undefined") {
    return () => {}
  }

  const handleStorage = (event: StorageEvent) => {
    if (
      event.key === null ||
      event.key === SELECTED_ORGANIZATION_STORAGE_KEY ||
      event.key === LEGACY_SELECTED_ORGANIZATION_STORAGE_KEY
    ) {
      callback(getStoredSelectedOrganization())
    }
  }

  const handleCustomEvent = (event: Event) => {
    const customEvent = event as CustomEvent<{ value?: string | null }>
    callback(customEvent.detail?.value ?? getStoredSelectedOrganization())
  }

  window.addEventListener("storage", handleStorage)
  window.addEventListener(SELECTED_ORGANIZATION_EVENT, handleCustomEvent)

  return () => {
    window.removeEventListener("storage", handleStorage)
    window.removeEventListener(SELECTED_ORGANIZATION_EVENT, handleCustomEvent)
  }
}
